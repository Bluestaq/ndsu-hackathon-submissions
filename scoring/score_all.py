#!/usr/bin/env python3
"""Score every merged submission and write results/results.json.

python scoring/score_all.py --submissions submissions --key KEY.json \
    --prs prs.json --output results/results.json [--lock-utc 2026-..Z] [--repo OWNER/REPO]

The answer key is passed as a file path and is never written to the output.
Results report the automated diagnostic only: supporting evidence for judges,
not the event score.

With --repo (and GH_TOKEN), each merged pull request's final commit is dated by the
earliest GitHub Actions run GitHub created for it. Commit dates can be backdated;
run creation times cannot, so a push after the deadline is flagged even if its
check later shows green.
"""
import argparse
import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scorer = load("scorer", ROOT / "scoring/score_submission.py")
validator = load("validator", ROOT / "starter/submission/validate_submission.py")
checker = load("checker", ROOT / ".github/scripts/check_submission_pr.py")


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pr_index(prs):
    """The pull request per author whose content is on main: the last merged one that
    touched that author's submission file, or else the earliest one."""
    index = {}
    for pr in prs or []:
        login = (pr.get("author") or {}).get("login", "")
        path = f"submissions/{login}/submission.json".lower()
        if not any(f.get("path", "").lower() == path for f in pr.get("files", [])):
            continue
        best = index.get(login.lower())
        if best is None:
            index[login.lower()] = pr
        elif pr.get("mergedAt") or best.get("mergedAt"):
            if not best.get("mergedAt") or (pr.get("mergedAt") and parse_time(pr["mergedAt"]) > parse_time(best["mergedAt"])):
                index[login.lower()] = pr
        elif parse_time(pr["createdAt"]) < parse_time(best["createdAt"]):
            index[login.lower()] = pr
    return index


def add_push_times(prs, fetch, repo):
    """Set headPushedAt on each merged PR: when GitHub first ran Actions for its final commit."""
    for pr in prs or []:
        sha = pr.get("headRefOid")
        if not (pr.get("mergedAt") and sha):
            continue
        runs = fetch(f"/repos/{repo}/actions/runs?head_sha={sha}&event=pull_request&per_page=100").get("workflow_runs", [])
        times = [r["created_at"] for r in runs if r.get("created_at")]
        pr["headPushedAt"] = min(times, key=parse_time) if times else None
    return prs


def score_all(submissions_dir, key, prs=None, lock_utc=None, grace_minutes=0):
    index = pr_index(prs)
    lock = parse_time(lock_utc) + timedelta(minutes=grace_minutes) if lock_utc else None
    entries = []
    for path in sorted(Path(submissions_dir).glob("*/submission.json")):
        folder = path.parent.name
        entry = {"github_handle": folder}
        try:
            raw = path.read_text()
            submission = json.loads(raw)
        except ValueError as error:
            entries.append({**entry, "valid": False, "problems": [f"invalid JSON: {error}"]})
            continue
        problems = validator.validate(submission)
        private_problems, _ = checker.privacy_findings(raw, submission)
        problems += private_problems
        participant = submission.get("participant", {}) if isinstance(submission, dict) else {}
        if isinstance(participant, dict) and str(participant.get("github_handle", "")).lower() != folder.lower():
            problems.append("participant.github_handle does not match the folder name")
        # Never publish a display name from a file that failed the privacy scan.
        if isinstance(participant, dict) and isinstance(participant.get("display_name"), str) and not private_problems:
            entry["display_name"] = participant["display_name"]
        if isinstance(submission, dict) and isinstance(submission.get("repository_url"), str):
            entry["repository_url"] = submission["repository_url"]
        pr = index.get(folder.lower())
        if pr:
            entry.update(pull_request=pr.get("number"), pull_request_url=pr.get("url"), submitted_at=pr["createdAt"])
            opened_late = bool(lock and parse_time(pr["createdAt"]) > lock)
            pushed_late = bool(lock and pr.get("headPushedAt") and parse_time(pr["headPushedAt"]) > lock)
            entry["late"] = opened_late or pushed_late
            if opened_late:
                problems.append(f"submitted after the deadline ({lock_utc})")
            elif pushed_late:
                problems.append(f"changed after the deadline ({lock_utc})")
        if problems:
            entries.append({**entry, "valid": False, "problems": problems})
            continue
        result = scorer.score(submission, key)
        entries.append({**entry, "valid": True,
                        "diagnostic_score": round(result["diagnostic_score"], 2),
                        "macro_f1": round(result["macro_f1"], 3),
                        "mean_timing_credit": round(result["mean_timing_credit"], 3),
                        "episodes_matched": sum(1 for e in result["episodes"] if e.get("correct")),
                        "episode_count": result["episode_count"],
                        "action_agreement": result["action_agreement"],
                        "false_positives": len(result["false_positives"])})
    entries.sort(key=lambda e: (not e["valid"], -e.get("diagnostic_score", 0), e["github_handle"].lower()))
    rank = 0
    for e in entries:
        if e["valid"]:
            rank += 1
            e["rank"] = rank
    return {"status": "scored", "scored_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "maximum": 40, "lock_utc": lock_utc,
            "note": "Automated diagnostic (25 × macro-F1 + 15 × mean onset credit). Supporting evidence for judges, "
                    "not the event score. The winner is chosen by the judges using the published 100-point rubric.",
            "entries": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submissions", default="submissions")
    parser.add_argument("--key", required=True)
    parser.add_argument("--prs")
    parser.add_argument("--lock-utc")
    parser.add_argument("--grace-minutes", type=int, default=0)
    parser.add_argument("--output", default="results/results.json")
    parser.add_argument("--repo", help="OWNER/REPO: date each merged PR's final commit from Actions runs (needs GH_TOKEN)")
    args = parser.parse_args()
    key = json.loads(Path(args.key).read_text())
    prs = json.loads(Path(args.prs).read_text()) if args.prs else None
    if args.repo and prs:
        token = os.environ["GH_TOKEN"]
        add_push_times(prs, lambda path: checker.api(path, token), args.repo)
    results = score_all(args.submissions, key, prs, args.lock_utc or None, args.grace_minutes)
    Path(args.output).write_text(json.dumps(results, indent=2) + "\n")
    valid = sum(e["valid"] for e in results["entries"])
    print(f"Scored {valid} valid of {len(results['entries'])} submission(s); wrote {args.output}.")


if __name__ == "__main__":
    main()
