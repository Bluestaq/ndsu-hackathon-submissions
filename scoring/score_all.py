#!/usr/bin/env python3
"""Score every merged submission and write results/results.json.

python scoring/score_all.py --submissions submissions --key KEY.json \
    --prs prs.json --output results/results.json [--lock-utc 2026-..Z]

The answer key is passed as a file path and is never written to the output.
Results report the automated diagnostic only: supporting evidence for judges,
not the event score.
"""
import argparse
import importlib.util
import json
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


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pr_index(prs):
    """Earliest pull request per author that touched that author's submission file."""
    index = {}
    for pr in prs or []:
        login = (pr.get("author") or {}).get("login", "")
        path = f"submissions/{login}/submission.json".lower()
        if not any(f.get("path", "").lower() == path for f in pr.get("files", [])):
            continue
        best = index.get(login.lower())
        if best is None or parse_time(pr["createdAt"]) < parse_time(best["createdAt"]):
            index[login.lower()] = pr
    return index


def score_all(submissions_dir, key, prs=None, lock_utc=None, grace_minutes=10):
    index = pr_index(prs)
    lock = parse_time(lock_utc) + timedelta(minutes=grace_minutes) if lock_utc else None
    entries = []
    for path in sorted(Path(submissions_dir).glob("*/submission.json")):
        folder = path.parent.name
        entry = {"github_handle": folder}
        try:
            submission = json.loads(path.read_text())
        except ValueError as error:
            entries.append({**entry, "valid": False, "problems": [f"invalid JSON: {error}"]})
            continue
        problems = validator.validate(submission)
        participant = submission.get("participant", {}) if isinstance(submission, dict) else {}
        if isinstance(participant, dict) and str(participant.get("github_handle", "")).lower() != folder.lower():
            problems.append("participant.github_handle does not match the folder name")
        if isinstance(participant, dict) and isinstance(participant.get("display_name"), str):
            entry["display_name"] = participant["display_name"]
        if isinstance(submission, dict) and isinstance(submission.get("repository_url"), str):
            entry["repository_url"] = submission["repository_url"]
        pr = index.get(folder.lower())
        if pr:
            entry.update(pull_request=pr.get("number"), pull_request_url=pr.get("url"), submitted_at=pr["createdAt"])
            entry["late"] = bool(lock and parse_time(pr["createdAt"]) > lock)
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
    parser.add_argument("--grace-minutes", type=int, default=10)
    parser.add_argument("--output", default="results/results.json")
    args = parser.parse_args()
    key = json.loads(Path(args.key).read_text())
    prs = json.loads(Path(args.prs).read_text()) if args.prs else None
    results = score_all(args.submissions, key, prs, args.lock_utc or None, args.grace_minutes)
    Path(args.output).write_text(json.dumps(results, indent=2) + "\n")
    valid = sum(e["valid"] for e in results["entries"])
    print(f"Scored {valid} valid of {len(results['entries'])} submission(s); wrote {args.output}.")


if __name__ == "__main__":
    main()
