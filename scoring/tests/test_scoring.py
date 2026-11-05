"""Meaningful scoring and validator regression checks. Run with unittest discovery."""
import copy
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scorer = load("scorer", ROOT / "scoring/score_submission.py")
validator = load("validator", ROOT / "starter/submission/validate_submission.py")
T0 = datetime(2026, 5, 6, tzinfo=timezone.utc)


def episode(start=60, end=120, cls="JAMMING", tractors=None, ident="E1"):
    return {
        "id": ident, "start": (T0 + timedelta(minutes=start)).isoformat(),
        "end": (T0 + timedelta(minutes=end)).isoformat(), "class": cls,
        "tractors": tractors or ["T1"], "recommended_action": "HALT_AND_REPORT",
    }


def detection(ep):
    return {
        **{k: v for k, v in ep.items() if k not in ("id", "recommended_action")},
        "action": ep["recommended_action"], "confidence": 0.8, "evidence": ["Measured evidence"],
    }


class ScoringTests(unittest.TestCase):
    def test_exact_matches_all_classes(self):
        key = {"episodes": [episode(start=60 + i * 120, end=120 + i * 120, cls=c, ident=str(i))
                            for i, c in enumerate(scorer.CLASSES)]}
        result = scorer.score({"detections": [detection(e) for e in key["episodes"]]}, key)
        self.assertEqual(result["diagnostic_score"], 40)

    def test_whole_day_guesses_fail(self):
        key = {"episodes": [episode(start=60 + i * 120, end=120 + i * 120, cls=c, ident=str(i))
                            for i, c in enumerate(scorer.CLASSES)]}
        dets = [detection(episode(start=0, end=1440, cls=c, tractors=["T1", "T2", "T3"]))
                for c in scorer.CLASSES for _ in range(2)]
        self.assertEqual(scorer.score({"detections": dets}, key)["diagnostic_score"], 0)

    def test_early_start_is_penalized(self):
        ep = episode()
        exact = scorer.score({"detections": [detection(ep)]}, {"episodes": [ep]})
        early = detection(episode(start=0, end=120))
        result = scorer.score({"detections": [early]}, {"episodes": [ep]})
        self.assertEqual(result["episodes"][0]["timing_credit"], 0)
        self.assertLess(result["diagnostic_score"], exact["diagnostic_score"])

    def test_duplicate_reduces_precision(self):
        ep = episode()
        result = scorer.score({"detections": [detection(ep), detection(ep)]}, {"episodes": [ep]})
        self.assertEqual(result["class_metrics"]["JAMMING"]["precision"], 0.5)

    def test_wrong_tractor_and_insufficient_tractor_agreement_fail(self):
        ep = episode(tractors=["T1"])
        for tractors in (["T2"], ["T1", "T2", "T3"]):
            d = detection(ep)
            d["tractors"] = tractors
            self.assertEqual(scorer.score({"detections": [d]}, {"episodes": [ep]})["diagnostic_score"], 0)

    def test_misclassification_has_no_timing_or_action_credit(self):
        ep = episode()
        d = detection(ep)
        d["class"] = "SPACE_WEATHER"
        result = scorer.score({"detections": [d]}, {"episodes": [ep]})
        self.assertTrue(result["episodes"][0]["matched"])
        self.assertEqual(result["diagnostic_score"], 0)
        self.assertEqual(result["action_agreement"], 0)

    def test_global_assignment_keeps_two_eligible_matches(self):
        key = {"episodes": [episode(60, 120, ident="A"), episode(120, 180, ident="B")]}
        broad = detection(episode(60, 180))
        narrow = detection(episode(60, 100))
        result = scorer.score({"detections": [broad, narrow]}, key)
        self.assertEqual(result["class_metrics"]["JAMMING"]["tp"], 2)

    def test_same_class_has_priority(self):
        ep = episode()
        wrong = detection(ep)
        wrong["class"] = "SPOOFING"
        correct = detection(episode(62, 118))
        result = scorer.score({"detections": [wrong, correct]}, {"episodes": [ep]})
        self.assertEqual(result["class_metrics"]["JAMMING"]["tp"], 1)
        self.assertEqual(result["class_metrics"]["SPOOFING"]["fp"], 1)

    def test_missed_episode_has_zero_credit(self):
        result = scorer.score({"detections": []}, {"episodes": [episode()]})
        self.assertEqual(result["diagnostic_score"], 0)

    def test_recurrent_multipath_exempt_but_duplicates_penalized(self):
        ep = episode(60, 60.1, cls="MULTIPATH")
        unrelated = detection(episode(70, 70.1, cls="MULTIPATH"))
        result = scorer.score(
            {"detections": [detection(ep), detection(ep), unrelated]}, {"episodes": [ep]},
        )
        self.assertEqual(result["benign_multipath_reports"], 1)
        self.assertEqual(result["class_metrics"]["MULTIPATH"]["fp"], 1)

    def test_order_does_not_change_assignment(self):
        eps = [episode(60, 120, ident="A"), episode(100, 160, ident="B")]
        dets = [detection(e) for e in eps]
        a = scorer.score({"detections": dets}, {"episodes": eps})
        b = scorer.score({"detections": list(reversed(dets))}, {"episodes": eps})
        self.assertEqual(a, b)


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.sub = {
            "participant": {"github_handle": "example-student", "display_name": "Example Student"},
            "repository_url": "https://github.com/example-student/straight-rows",
            "detections": [detection(episode())],
        }

    def test_valid_submission_and_utc_z(self):
        self.assertEqual(validator.validate(self.sub), [])
        self.sub["detections"][0]["start"] = "2026-05-06T01:00:00Z"
        self.assertEqual(validator.validate(self.sub), [])

    def test_bad_shapes_never_crash(self):
        for bad in ([], None, {"participant": [], "detections": [None]},
                    {"participant": {"github_handle": 2}, "detections": [{"tractors": [{}]}]}):
            self.assertTrue(validator.validate(bad))

    def test_private_details_rejected(self):
        for field in ("email", "student_id", "Student-ID"):
            sub = copy.deepcopy(self.sub)
            sub["participant"][field] = "x"
            self.assertTrue(any("must not be included" in p for p in validator.validate(sub)))
        sub = copy.deepcopy(self.sub)
        sub["candidate"] = {"name": "A", "email": "a@ndsu.edu", "student_id": "1"}
        self.assertTrue(any("candidate" in p for p in validator.validate(sub)))
        sub = copy.deepcopy(self.sub)
        sub["participant"]["display_name"] = "me@ndsu.edu"
        self.assertTrue(validator.validate(sub))

    def test_handle_and_repository_checked(self):
        for handle in ("your-github-username", "-bad", "a" * 40, "has space"):
            sub = copy.deepcopy(self.sub)
            sub["participant"]["github_handle"] = handle
            self.assertTrue(validator.validate(sub))
        for url in ("http://github.com/example-student/x", "https://gitlab.com/example-student/x",
                    "https://github.com/someone-else/x", "https://github.com/your-github-username/your-solution-repo"):
            sub = copy.deepcopy(self.sub)
            sub["repository_url"] = url
            self.assertTrue(validator.validate(sub))
        sub = copy.deepcopy(self.sub)
        del sub["participant"]["display_name"]
        self.assertEqual(validator.validate(sub), [])

    def test_nonfinite_or_boolean_confidence_rejected(self):
        for value in (True, float("nan"), float("inf"), -0.1, 1.1):
            sub = copy.deepcopy(self.sub)
            sub["detections"][0]["confidence"] = value
            self.assertTrue(validator.validate(sub))

    def test_interval_end_and_timezone_rejected(self):
        for field, value in (("end", "2026-05-07T00:00:01Z"),
                             ("end", "2026-05-06T01:00:00Z"),
                             ("start", "2026-05-06T01:00:00"),
                             ("start", "2026-05-05T23:59:59Z")):
            sub = copy.deepcopy(self.sub)
            sub["detections"][0][field] = value
            self.assertTrue(validator.validate(sub))

    def test_duplicate_tractors_rejected(self):
        self.sub["detections"][0]["tractors"] = ["T1", "T1"]
        self.assertTrue(validator.validate(self.sub))


if __name__ == "__main__":
    unittest.main()
