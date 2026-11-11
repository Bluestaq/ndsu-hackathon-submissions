"""Guards for the judges' scoring page (site/judge/). The page is public, so it must hold no secrets."""
import base64
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "site/judge/index.html"
KEY = ROOT / "site/judge/key.json"
TOKEN = re.compile(r"\b(?:gh[opsur]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")


class JudgePage(unittest.TestCase):
    def test_script_hash_in_csp_is_current(self):
        result = subprocess.run([sys.executable, str(ROOT / ".github/scripts/judge_csp.py"), "--check"])
        self.assertEqual(result.returncode, 0, "run python .github/scripts/judge_csp.py after editing the page")

    def test_no_github_tokens_anywhere_in_the_site(self):
        for path in (ROOT / "site").rglob("*"):
            if path.is_file() and path.suffix in {".html", ".json", ".js", ".txt", ".md"}:
                self.assertIsNone(TOKEN.search(path.read_text(errors="ignore")), f"token-like string in {path}")

    def test_untrusted_text_is_never_parsed_as_html(self):
        html = PAGE.read_text()
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(sink, html)

    def test_public_key_file_holds_only_a_consistent_public_key(self):
        key = json.loads(KEY.read_text())
        self.assertLessEqual(set(key), {"publicKey", "kid", "note"})
        self.assertNotIn("PRIVATE", KEY.read_text())
        if key["publicKey"]:
            der = base64.b64decode(key["publicKey"], validate=True)
            self.assertEqual(key["kid"], hashlib.sha256(der).hexdigest()[:16])


if __name__ == "__main__":
    unittest.main()
