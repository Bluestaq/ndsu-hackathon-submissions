#!/usr/bin/env python3
"""Straight Rows diagnostic scorer. Supporting evidence, not the event rubric.

python score_submission.py submission.json eval_episodes_ANSWER_KEY.json [--json results.json]
"""
import argparse
import json
from datetime import datetime

CLASSES = ["SPACE_WEATHER", "JAMMING", "SPOOFING", "EQUIPMENT_FAULT", "MULTIPATH"]
FULL_S, ZERO_S = 300.0, 3600.0
MIN_TIME_IOU, MIN_TRACTOR_IOU = 0.30, 0.50


def iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def overlap_metrics(detection, episode):
    a, b = iso(detection["start"]), iso(detection["end"])
    c, d = iso(episode["start"]), iso(episode["end"])
    intersection = max(0.0, (min(b, d) - max(a, c)).total_seconds())
    union = (max(b, d) - min(a, c)).total_seconds()
    time_iou = intersection / union if union > 0 else 0.0
    dt, et = set(detection["tractors"]), set(episode["tractors"])
    tractor_iou = len(dt & et) / len(dt | et) if dt | et else 0.0
    return time_iou, tractor_iou


def _assign(detections, episodes, available_d, available_e, same_class):
    """Maximum cardinality, then summed temporal IoU, then tractor IoU.

    Dynamic programming over the eight truth episodes gives exact assignment.
    Remaining ties prefer earlier sorted detections.
    """
    available_e = sorted(available_e)
    states = {0: ((0.0, 0.0), ())}
    for di in sorted(available_d):
        edges = []
        for bit, ei in enumerate(available_e):
            ep, det = episodes[ei], detections[di]
            if same_class and det["class"] != ep["class"]:
                continue
            ti, tr = overlap_metrics(det, ep)
            if ti >= MIN_TIME_IOU and tr >= MIN_TRACTOR_IOU:
                edges.append((bit, ei, ti, tr))
        if not edges:
            continue
        updated = dict(states)
        for mask, (weight, pairs) in states.items():
            for bit, ei, ti, tr in edges:
                if mask & (1 << bit):
                    continue
                new_mask = mask | (1 << bit)
                new_weight = (weight[0] + ti, weight[1] + tr)
                new_pairs = pairs + ((ei, di),)
                old = updated.get(new_mask)
                if old is None or new_weight > old[0] or (
                    new_weight == old[0] and new_pairs < old[1]
                ):
                    updated[new_mask] = (new_weight, new_pairs)
        states = updated
    best = min(
        states,
        key=lambda mask: (
            -mask.bit_count(), -states[mask][0][0],
            -states[mask][0][1], states[mask][1],
        ),
    )
    return dict(states[best][1])


def score(submission, key):
    episodes = key["episodes"]
    detections = sorted(
        submission.get("detections", []),
        key=lambda d: (iso(d["start"]), iso(d["end"]), d["class"], tuple(sorted(d["tractors"]))),
    )
    for d in detections:
        if d["class"] not in CLASSES or iso(d["end"]) <= iso(d["start"]):
            raise ValueError("Invalid detection class or interval")
    matches = _assign(detections, episodes, range(len(detections)), range(len(episodes)), True)
    matches.update(_assign(
        detections, episodes,
        set(range(len(detections))) - set(matches.values()),
        set(range(len(episodes))) - set(matches),
        False,
    ))
    used = set(matches.values())
    counts = {c: {"tp": 0, "fp": 0, "fn": 0} for c in CLASSES}
    records, timing_credits = [], []
    action_ok = 0
    for ei, ep in enumerate(episodes):
        record = {"episode": ep["id"], "truth_class": ep["class"], "matched": ei in matches}
        if ei not in matches:
            counts[ep["class"]]["fn"] += 1
            timing_credits.append(0.0)
            record.update(correct=False, action_agreement=False)
        else:
            d = detections[matches[ei]]
            correct = d["class"] == ep["class"]
            if correct:
                counts[ep["class"]]["tp"] += 1
            else:
                counts[ep["class"]]["fn"] += 1
                counts[d["class"]]["fp"] += 1
            signed_error = (iso(d["start"]) - iso(ep["start"])).total_seconds()
            error = abs(signed_error)
            credit = 1.0 if error <= FULL_S else max(0.0, (ZERO_S - error) / (ZERO_S - FULL_S))
            timing_credits.append(credit if correct else 0.0)
            action_agreement = correct and d.get("action") == ep.get("recommended_action")
            action_ok += action_agreement
            ti, tr = overlap_metrics(d, ep)
            record.update(
                correct=correct, predicted_class=d["class"],
                start=d["start"], end=d["end"], tractors=d["tractors"],
                onset_error_s=signed_error, time_iou=ti, tractor_iou=tr,
                timing_credit=credit if correct else 0.0,
                action_agreement=action_agreement,
            )
        records.append(record)
    false_positives, benign = [], 0
    for di, d in enumerate(detections):
        if di in used:
            continue
        duration = (iso(d["end"]) - iso(d["start"])).total_seconds()
        # Recurrent short multipath reports are permitted. A short duplicate
        # overlapping the representative truth window is still a false positive.
        overlaps_representative = any(
            ep["class"] == "MULTIPATH"
            and max(iso(d["start"]), iso(ep["start"])) < min(iso(d["end"]), iso(ep["end"]))
            and set(d["tractors"]) & set(ep["tractors"])
            for ep in episodes
        )
        if d["class"] == "MULTIPATH" and duration <= 180 and not overlaps_representative:
            benign += 1
            continue
        counts[d["class"]]["fp"] += 1
        false_positives.append(d)
    for c, n in counts.items():
        n["precision"] = n["tp"] / (n["tp"] + n["fp"]) if n["tp"] + n["fp"] else 0.0
        n["recall"] = n["tp"] / (n["tp"] + n["fn"]) if n["tp"] + n["fn"] else 0.0
        denom = 2 * n["tp"] + n["fp"] + n["fn"]
        n["f1"] = 2 * n["tp"] / denom if denom else 0.0
    macro_f1 = sum(n["f1"] for n in counts.values()) / len(CLASSES)
    timing = sum(timing_credits) / len(episodes) if episodes else 0.0
    return {
        "diagnostic_score": 25 * macro_f1 + 15 * timing,
        "maximum": 40, "macro_f1": macro_f1, "mean_timing_credit": timing,
        "class_metrics": counts, "episodes": records,
        "action_agreement": action_ok, "episode_count": len(episodes),
        "false_positives": false_positives, "benign_multipath_reports": benign,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission")
    parser.add_argument("answer_key")
    parser.add_argument("--json", dest="json_output")
    args = parser.parse_args()
    with open(args.submission) as f:
        submission = json.load(f)
    with open(args.answer_key) as f:
        key = json.load(f)
    result = score(submission, key)
    for ep in result["episodes"]:
        status = ep.get("predicted_class", "MISSED")
        error = f'{ep["onset_error_s"] / 60:+.1f} min' if "onset_error_s" in ep else "-"
        print(f'{ep["episode"]:8} {ep["truth_class"]:16} {status:16} {error:>10}')
    for c, m in result["class_metrics"].items():
        print(f'{c:16} P={m["precision"]:.3f} R={m["recall"]:.3f} F1={m["f1"]:.3f}')
    print(f'DIAGNOSTIC SCORE: {result["diagnostic_score"]:.2f}/40 (supporting evidence only)')
    print(f'Action agreement: {result["action_agreement"]}/{result["episode_count"]}; '
          f'false positives: {len(result["false_positives"])}; '
          f'benign multipath reports: {result["benign_multipath_reports"]}')
    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
