#!/usr/bin/env python3
"""Check a submission pull request without running any participant code.

Runs from the base branch (trusted code). It reads the pull request's single
submission file as data through the GitHub API, then applies the starter
validator plus pull-request rules:

  * exactly one changed file: submissions/<pr-author>/submission.json
  * participant.github_handle and the repository owner match the PR author
  * the solution repository is public
  * opened, and last updated, before the deadline (SUBMISSION_LOCK_UTC, if set).
    A push or reopen after the deadline makes the submission late.

Environment: GH_TOKEN, REPO, PR_NUMBER, AUTHOR, HEAD_REPO, HEAD_SHA, CREATED_AT,
EVENT_ACTION, SUBMISSION_LOCK_UTC (optional, ISO 8601), SUBMISSION_GRACE_MINUTES
(optional, default 0).
"""
import base64
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 1_000_000
API = "https://api.github.com"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validator", ROOT / "starter/submission/validate_submission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def api(path, token, allow_404=False):
    request = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "straight-rows-check"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        if allow_404 and error.code == 404:
            return None
        raise


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check(env, fetch, validator):
    """Return (errors, warnings, summary_lines). `fetch(path, allow_404)` calls the API."""
    errors, warnings, lines = [], [], []
    author = env["AUTHOR"]
    expected = f"submissions/{author}/submission.json".lower()
    files = fetch(f"/repos/{env['REPO']}/pulls/{env['PR_NUMBER']}/files?per_page=100", False)
    names = [f["filename"] for f in files]
    if len(files) != 1 or names[0].lower() != expected:
        errors.append(f"Change exactly one file, `submissions/{author}/submission.json`. This pull request changes: "
                      + ", ".join(f"`{n}`" for n in names[:10]))
        return errors, warnings, lines
    entry = files[0]
    if entry["status"] not in ("added", "modified"):
        errors.append("The submission file must be added or modified, not removed or renamed.")
        return errors, warnings, lines
    content = fetch(f"/repos/{env['HEAD_REPO']}/contents/{entry['filename']}?ref={env['HEAD_SHA']}", False)
    if content.get("size", 0) > MAX_BYTES or content.get("encoding") != "base64":
        errors.append("submission.json must be a normal file under 1 MB.")
        return errors, warnings, lines
    try:
        submission = json.loads(base64.b64decode(content["content"]))
    except ValueError as error:
        errors.append(f"submission.json is not valid JSON ({error}).")
        return errors, warnings, lines
    errors += validator.validate(submission)
    participant = submission.get("participant") if isinstance(submission, dict) else None
    handle = participant.get("github_handle") if isinstance(participant, dict) else None
    if isinstance(handle, str) and handle.lower() != author.lower():
        errors.append(f"participant.github_handle is `{handle}`, but the pull request was opened by `{author}`.")
    url = submission.get("repository_url", "") if isinstance(submission, dict) else ""
    if isinstance(url, str) and url.startswith("https://github.com/"):
        parts = url.rstrip("/").split("/")
        if len(parts) >= 5:
            repo = fetch(f"/repos/{parts[3]}/{parts[4]}", True)
            if repo is None or repo.get("private"):
                errors.append(f"Your solution repository {url} is not public yet. Make it public at hour 22.")
            else:
                lines.append(f"Solution repository is public: {url}")
    lock = env.get("SUBMISSION_LOCK_UTC", "").strip()
    if lock:
        deadline = parse_time(lock) + timedelta(minutes=int(env.get("SUBMISSION_GRACE_MINUTES") or 0))
        opened = parse_time(env["CREATED_AT"])
        now = parse_time(env["NOW"]) if env.get("NOW") else datetime.now(timezone.utc)
        if opened > deadline:
            errors.append(f"Submissions closed at {lock}. This pull request was opened at {env['CREATED_AT']}, after the deadline.")
        elif env.get("EVENT_ACTION") in ("synchronize", "reopened") and now > deadline:
            errors.append(f"Submissions closed at {lock}. This pull request was changed after the deadline, so it is late.")
        else:
            lines.append(f"Opened at {env['CREATED_AT']}, before the deadline ({lock}).")
    if isinstance(submission, dict) and isinstance(submission.get("detections"), list):
        lines.append(f"{len(submission['detections'])} detection(s) found.")
    return errors, warnings, lines


def main():
    env = {k: os.environ.get(k, "") for k in ("REPO", "PR_NUMBER", "AUTHOR", "HEAD_REPO", "HEAD_SHA", "CREATED_AT",
                                                "EVENT_ACTION", "SUBMISSION_LOCK_UTC", "SUBMISSION_GRACE_MINUTES")}
    token = os.environ["GH_TOKEN"]
    errors, warnings, lines = check(env, lambda path, allow: api(path, token, allow), load_validator())
    summary = ["## Straight Rows submission check", ""]
    summary += [f"- {line}" for line in lines]
    summary += [f"- ⚠️ {w}" for w in warnings]
    if errors:
        summary += ["", "**Please fix:**"] + [f"- {e}" for e in errors]
    else:
        summary += ["", "**Format check passed.** This checks structure only, not correctness. Scoring runs after the lock."]
    text = "\n".join(summary) + "\n"
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text)
    for w in warnings:
        print(f"::warning::{w}")
    for e in errors:
        print(f"::error::{e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
