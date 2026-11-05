#!/usr/bin/env python3
"""Validate a Straight Rows submission.json before you submit.

Usage:  python validate_submission.py submission.json
Exits 0 and prints OK if the file is well-formed; otherwise lists problems.

Identify yourself only by GitHub username. Do NOT put your email address or
student ID in this file: submissions are public. Bluestaq University Programs
already has your registration details.
"""
import json
import math
import re
import sys
from datetime import datetime

CLASSES = {"SPACE_WEATHER", "JAMMING", "SPOOFING", "EQUIPMENT_FAULT", "MULTIPATH"}
ACTIONS = {"HALT_OR_DEGRADED_MODE", "HALT_AND_REPORT",
           "HALT_CROSSCHECK_AND_REPORT", "SERVICE_MACHINE_OTHERS_CONTINUE",
           "CONTINUE_FALSE_ALARM"}
TRACTORS = {"T1", "T2", "T3"}
EVAL_START = datetime.fromisoformat("2026-05-06T00:00:00+00:00")
EVAL_END = datetime.fromisoformat("2026-05-07T00:00:00+00:00")
HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")
REPO_URL = re.compile(r"^https://github\.com/[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}/?$")
PLACEHOLDERS = ("your-github-username", "your-solution-repo", "Optional name")
PRIVATE_FIELDS = ("email", "student_id", "studentid", "phone", "ndsu_id")
MAX_DETECTIONS = 500


def validate(sub):
    problems = []
    if not isinstance(sub, dict):
        return ["submission must be a JSON object"]

    if "candidate" in sub:
        problems.append("remove the old 'candidate' block; use 'participant' with your GitHub username "
                        "(never put your email or student ID in a public submission)")
    part = sub.get("participant", {})
    if not isinstance(part, dict):
        problems.append("participant must be an object")
        part = {}
    for key in part:
        if str(key).lower().replace("-", "_") in PRIVATE_FIELDS:
            problems.append(f"participant.{key} must not be included: submissions are public")
    handle = part.get("github_handle", "")
    if not isinstance(handle, str) or not HANDLE.match(handle) or handle in PLACEHOLDERS:
        problems.append("participant.github_handle must be your GitHub username")
    name = part.get("display_name", "")
    if name is not None and (not isinstance(name, str) or len(name) > 60 or "@" in name
                             or name.startswith(PLACEHOLDERS)):
        problems.append("participant.display_name is optional; if given, use up to 60 characters and no email address")
    url = sub.get("repository_url", "")
    if not isinstance(url, str) or not REPO_URL.match(url) or any(p in url for p in PLACEHOLDERS):
        problems.append("repository_url must be your solution repository, https://github.com/<you>/<repo>")
    elif isinstance(handle, str) and handle and url.split("/")[3].lower() != handle.lower():
        problems.append("repository_url should be a repository you own (github.com/<your username>/...)")

    dets = sub.get("detections")
    if not isinstance(dets, list) or not dets:
        problems.append("detections must be a non-empty list")
        dets = []
    elif len(dets) > MAX_DETECTIONS:
        problems.append(f"detections has {len(dets)} entries; the limit is {MAX_DETECTIONS}")
        dets = []

    for i, d in enumerate(dets):
        tag = f"detections[{i}]"
        if not isinstance(d, dict):
            problems.append(f"{tag} must be an object")
            continue
        try:
            a = datetime.fromisoformat(d["start"].replace("Z", "+00:00"))
            b = datetime.fromisoformat(d["end"].replace("Z", "+00:00"))
            if a.utcoffset() is None or b.utcoffset() is None:
                raise ValueError("Timezone offset required")
            if not (EVAL_START <= a < EVAL_END):
                problems.append(f"{tag}.start outside the evaluation window")
            if b <= a:
                problems.append(f"{tag}: end must be after start")
            if b > EVAL_END:
                problems.append(f"{tag}.end outside the evaluation window")
        except Exception:
            problems.append(f"{tag}: start/end must be ISO-8601 timestamps with a timezone")
        if not isinstance(d.get("class"), str) or d["class"] not in CLASSES:
            problems.append(f"{tag}.class must be one of {sorted(CLASSES)}")
        if not isinstance(d.get("action"), str) or d["action"] not in ACTIONS:
            problems.append(f"{tag}.action must be one of {sorted(ACTIONS)}")
        trs = d.get("tractors", [])
        if (not isinstance(trs, list) or not trs
                or not all(isinstance(t, str) and t in TRACTORS for t in trs)
                or len(set(trs)) != len(trs)):
            problems.append(f"{tag}.tractors must be a non-empty list of distinct T1/T2/T3 IDs")
        c = d.get("confidence")
        if (isinstance(c, bool) or not isinstance(c, (int, float))
                or not math.isfinite(c) or not 0.0 <= c <= 1.0):
            problems.append(f"{tag}.confidence must be a number in [0,1]")
        ev = d.get("evidence", [])
        if not isinstance(ev, list) or not ev or not all(
                isinstance(s, str) and s.strip() for s in ev):
            problems.append(f"{tag}.evidence must be a non-empty list of strings")
    return problems


def main(path):
    try:
        with open(path) as f:
            sub = json.load(f)
    except Exception as e:
        print(f"FAIL: cannot parse JSON ({e})")
        return 1
    problems = validate(sub)

    if problems:
        print(f"FAIL: {len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print(f"OK: {len(sub['detections'])} detection(s); submission is well-formed.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
