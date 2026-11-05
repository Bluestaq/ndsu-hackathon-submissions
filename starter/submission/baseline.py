#!/usr/bin/env python3
"""Starter baseline: intentionally ignores S4, RFI, advisories, and multipath.

python submission/baseline.py --data data --output submission.json \
    --github-handle YOUR_GITHUB_USERNAME \
    --repo-url https://github.com/YOUR_GITHUB_USERNAME/YOUR_SOLUTION_REPO

Submissions are public: never add your email address or student ID.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

ACTION = {
    "SPACE_WEATHER": "HALT_OR_DEGRADED_MODE",
    "JAMMING": "HALT_AND_REPORT",
    "SPOOFING": "HALT_CROSSCHECK_AND_REPORT",
    "EQUIPMENT_FAULT": "SERVICE_MACHINE_OTHERS_CONTINUE",
    "MULTIPATH": "CONTINUE_FALSE_ALARM",
}
EVAL_START = pd.Timestamp("2026-05-06T00:00:00Z")
EVAL_END = pd.Timestamp("2026-05-07T00:00:00Z")


def detect(data):
    data = Path(data)
    tele = pd.read_csv(data / "farm/tractor_telemetry.csv.gz", parse_dates=["ts"])
    with open(data / "sda/sgi_indices.json") as f:
        kp = pd.DataFrame(json.load(f)["kp"])
    kp["ts"] = pd.to_datetime(kp["ts"], utc=True)
    feat = (
        tele.set_index("ts").groupby("tractor_id").resample("1min", include_groups=False)
        .agg(cn0=("mean_cn0_dbhz", "mean"), min_cn0=("min_cn0_dbhz", "min"),
             xte=("cross_track_error_m", "mean"), moving=("speed_mps", "mean"),
             link=("base_link_ok", "mean")).reset_index()
    )
    feat = pd.merge_asof(feat.sort_values("ts"), kp.sort_values("ts"), on="ts")
    ev = feat[(feat.ts >= EVAL_START) & (feat.ts < EVAL_END)].sort_values(["tractor_id", "ts"]).copy()
    ev["cn0_low"] = ev.cn0 < 38
    ev["xte_hi"] = (ev.xte > 1.0) & (ev.moving > 1)
    n_low = ev.groupby("ts")["cn0_low"].transform("sum")

    def classify(r, number_low):
        if r.cn0_low and number_low == 3 and r.kp >= 5:
            return "SPACE_WEATHER"
        if r.cn0_low and r.kp < 5:
            return "JAMMING"
        if r.xte_hi and not r.cn0_low:
            return "SPOOFING"
        if r.link < 0.7 or (r.min_cn0 < 20 and not r.cn0_low):
            return "EQUIPMENT_FAULT"
        return None

    ev["det"] = [classify(r, n) for r, n in zip(ev.itertuples(), n_low)]
    detections = []
    for tr, grp in ev.groupby("tractor_id"):
        current = None
        for r in grp.itertuples():
            if current and r.det != current["class"]:
                detections.append(current)
                current = None
            if r.det:
                if current is None:
                    current = {"start": r.ts, "end": r.ts, "class": r.det, "tractors": [tr]}
                current["end"] = min(r.ts + pd.Timedelta(minutes=1), EVAL_END)
        if current:
            detections.append(current)
    detections = [d for d in detections if (d["end"] - d["start"]).total_seconds() >= 180]
    merged = []
    for d in sorted(detections, key=lambda d: d["start"]):
        hit = next((m for m in merged if m["class"] == d["class"]
                    and d["start"] <= m["end"] + pd.Timedelta(minutes=5)), None)
        if hit:
            hit["end"] = max(hit["end"], d["end"])
            hit["tractors"] = sorted(set(hit["tractors"]) | set(d["tractors"]))
        else:
            merged.append(dict(d))
    return [
        {
            **d, "start": d["start"].isoformat(), "end": d["end"].isoformat(),
            "action": ACTION[d["class"]], "confidence": 0.5,
            "evidence": [
                f"Starter threshold rule identified {d['class']} on {','.join(d['tractors'])} "
                f"from {d['start'].isoformat()} to {d['end'].isoformat()}.",
                "This baseline uses Kp but does not corroborate with S4, advisories, or RFI. "
                "Review its attribution and replace this evidence with measured values.",
            ],
        }
        for d in merged
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data")
    parser.add_argument("--output", default="submission.json")
    parser.add_argument("--github-handle", required=True, help="your GitHub username")
    parser.add_argument("--repo-url", required=True, help="https://github.com/<you>/<your solution repo>")
    parser.add_argument("--display-name", default=None, help="optional name for the results page")
    args = parser.parse_args()
    participant = {"github_handle": args.github_handle}
    if args.display_name:
        participant["display_name"] = args.display_name
    submission = {
        "participant": participant,
        "repository_url": args.repo_url,
        "detections": detect(args.data),
    }
    with open(args.output, "w") as f:
        json.dump(submission, f, indent=2)
    print(f"Wrote {len(submission['detections'])} baseline detections to {args.output}")


if __name__ == "__main__":
    main()
