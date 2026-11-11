#!/usr/bin/env python3
"""Pin the judging page's inline script in its Content-Security-Policy.

python .github/scripts/judge_csp.py          # rewrite the hash after editing site/judge/index.html
python .github/scripts/judge_csp.py --check  # exit 1 if the hash is stale (used by the tests)
"""
import base64
import hashlib
import re
import sys
from pathlib import Path

PAGE = Path(__file__).resolve().parents[2] / "site/judge/index.html"
SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)
PIN = re.compile(r"script-src 'sha256-[^']*'")


def expected(html):
    scripts = SCRIPT.findall(html)
    if len(scripts) != 1:
        raise SystemExit(f"expected exactly one inline script, found {len(scripts)}")
    return "script-src 'sha256-" + base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode() + "'"


def main():
    html = PAGE.read_text()
    pin = expected(html)
    current = PIN.search(html)
    if "--check" in sys.argv:
        return 0 if current and current.group(0) == pin else 1
    PAGE.write_text(PIN.sub(pin, html, count=1))
    print(pin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
