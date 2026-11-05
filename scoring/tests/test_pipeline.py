"""Tests for the batch scorer and the pull-request checker. No network, no real answer key."""
import base64
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


score_all = load("score_all", ROOT / "scoring/score_all.py")
checker = load("checker", ROOT / ".github/scripts/check_submission_pr.py")
validator = load("validator", ROOT / "starter/submission/validate_submission.py")
T0 = datetime(2026, 5, 6, tzinfo=timezone.utc)
KEY = {"episodes": [{"id": "E1", "start": (T0 + timedelta(hours=1)).isoformat(), "end": (T0 + timedelta(hours=2)).isoformat(),
                     "class": "JAMMING", "tractors": ["T1"], "recommended_action": "HALT_AND_REPORT"}]}


def submission(handle, start_hours=1.0, cls="JAMMING"):
    start = T0 + timedelta(hours=start_hours)
    return {"participant": {"github_handle": handle}, "repository_url": f"https://github.com/{handle}/straight-rows",
            "detections": [{"start": start.isoformat(), "end": (start + timedelta(hours=1)).isoformat(), "tractors": ["T1"],
                            "class": cls, "action": "HALT_AND_REPORT", "confidence": 0.9, "evidence": ["x"]}]}


class ScoreAllTests(unittest.TestCase):
    def test_ranks_valid_entries_and_flags_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            for handle, sub in [("alice", submission("alice")), ("bob", submission("bob", cls="SPOOFING")),
                                ("carol", {**submission("carol"), "participant": {"github_handle": "someone"}})]:
                (Path(tmp) / handle).mkdir()
                (Path(tmp) / handle / "submission.json").write_text(json.dumps(sub))
            prs = [{"number": 7, "author": {"login": "alice"}, "createdAt": "2026-12-01T22:05:00Z", "url": "u",
                    "files": [{"path": "submissions/alice/submission.json"}]}]
            out = score_all.score_all(tmp, KEY, prs, "2026-12-01T22:10:00Z", 0)
        by = {e["github_handle"]: e for e in out["entries"]}
        self.assertEqual(by["alice"]["rank"], 1)
        # Macro-F1 averages all five classes, so a one-class key caps the diagnostic at 25/5 + 15 = 20.
        expected = score_all.scorer.score(submission("alice"), KEY)["diagnostic_score"]
        self.assertEqual(by["alice"]["diagnostic_score"], round(expected, 2))
        self.assertGreater(by["alice"]["diagnostic_score"], by["bob"]["diagnostic_score"])
        self.assertFalse(by["alice"]["late"])
        self.assertEqual(by["bob"]["rank"], 2)
        self.assertFalse(by["carol"]["valid"])
        # Per-episode truth is never published: no episode records and no answer-key timestamps.
        self.assertTrue(all("episodes" not in e for e in out["entries"]))
        self.assertNotIn(KEY["episodes"][0]["start"], json.dumps(out))

    def test_late_submission_is_not_scored(self):
        prs = [{"number": 1, "author": {"login": "alice"}, "createdAt": "2026-12-01T22:00:01Z",
                "files": [{"path": "submissions/alice/submission.json"}]}]
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "alice").mkdir()
            (Path(tmp) / "alice" / "submission.json").write_text(json.dumps(submission("alice")))
            out = score_all.score_all(tmp, KEY, prs, "2026-12-01T22:00:00Z", 0)
        entry = out["entries"][0]
        self.assertTrue(entry["late"])
        self.assertFalse(entry["valid"])
        self.assertNotIn("rank", entry)


class CheckerTests(unittest.TestCase):
    def env(self, **extra):
        return {"REPO": "Bluestaq/ndsu-hackathon-submissions", "PR_NUMBER": "3", "AUTHOR": "alice", "HEAD_REPO": "alice/fork",
                "HEAD_SHA": "abc", "CREATED_AT": "2026-12-01T21:59:00Z", "SUBMISSION_LOCK_UTC": "", **extra}

    def fake(self, files, sub, repo_public=True):
        def fetch(path, allow_404):
            if path.endswith("/files?per_page=100"):
                return files
            if "/contents/" in path:
                return {"size": 100, "encoding": "base64", "content": base64.b64encode(json.dumps(sub).encode()).decode()}
            return {"private": False} if repo_public else None
        return fetch

    def test_valid_pull_request_passes(self):
        files = [{"filename": "submissions/alice/submission.json", "status": "added"}]
        errors, warnings, _ = checker.check(self.env(), self.fake(files, submission("alice")), validator)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_extra_files_wrong_folder_and_handle_rejected(self):
        two = [{"filename": "submissions/alice/submission.json", "status": "added"},
               {"filename": ".github/workflows/x.yml", "status": "added"}]
        self.assertTrue(checker.check(self.env(), self.fake(two, submission("alice")), validator)[0])
        other = [{"filename": "submissions/bob/submission.json", "status": "added"}]
        self.assertTrue(checker.check(self.env(), self.fake(other, submission("alice")), validator)[0])
        files = [{"filename": "submissions/alice/submission.json", "status": "added"}]
        self.assertTrue(checker.check(self.env(), self.fake(files, submission("mallory")), validator)[0])

    def test_private_repository_and_late_submission(self):
        files = [{"filename": "submissions/alice/submission.json", "status": "added"}]
        errors, _, _ = checker.check(self.env(), self.fake(files, submission("alice"), repo_public=False), validator)
        self.assertTrue(any("not public" in e for e in errors))
        lock = {"SUBMISSION_LOCK_UTC": "2026-12-01T22:00:00Z", "SUBMISSION_GRACE_MINUTES": "0"}
        late = self.env(CREATED_AT="2026-12-01T22:00:01Z", **lock)
        errors, _, _ = checker.check(late, self.fake(files, submission("alice")), validator)
        self.assertTrue(any("after the deadline" in e for e in errors))
        on_time = self.env(CREATED_AT="2026-12-01T21:59:59Z", NOW="2026-12-01T21:59:59Z", EVENT_ACTION="opened", **lock)
        self.assertEqual(checker.check(on_time, self.fake(files, submission("alice")), validator)[0], [])

    def test_push_after_deadline_is_late(self):
        files = [{"filename": "submissions/alice/submission.json", "status": "modified"}]
        lock = {"SUBMISSION_LOCK_UTC": "2026-12-01T22:00:00Z", "SUBMISSION_GRACE_MINUTES": "0"}
        pushed_late = self.env(CREATED_AT="2026-12-01T21:00:00Z", NOW="2026-12-01T22:05:00Z", EVENT_ACTION="synchronize", **lock)
        errors, _, _ = checker.check(pushed_late, self.fake(files, submission("alice")), validator)
        self.assertTrue(any("changed after the deadline" in e for e in errors))
        title_edit = self.env(CREATED_AT="2026-12-01T21:00:00Z", NOW="2026-12-01T22:05:00Z", EVENT_ACTION="edited", **lock)
        self.assertEqual(checker.check(title_edit, self.fake(files, submission("alice")), validator)[0], [])

    def test_email_in_submission_rejected(self):
        files = [{"filename": "submissions/alice/submission.json", "status": "added"}]
        sub = submission("alice")
        sub["participant"]["email"] = "alice@ndsu.edu"
        self.assertTrue(checker.check(self.env(), self.fake(files, sub), validator)[0])


if __name__ == "__main__":
    unittest.main()
