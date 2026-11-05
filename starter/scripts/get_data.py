#!/usr/bin/env python3
"""Download the Straight Rows dataset (released at kickoff) into starter/data/.

python starter/scripts/get_data.py            # from the repository root
python starter/scripts/get_data.py --zip PATH # use a ZIP you already downloaded

Verifies the SHA-256 published in starter/DATASET_SHA256 and extracts only the
data/ folder from the official student package.
"""
import argparse
import hashlib
import io
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

URL = "https://github.com/Bluestaq/ndsu-hackathon-submissions/releases/latest/download/StraightRows_Student_Package.zip"
STARTER = Path(__file__).resolve().parents[1]
PREFIX = "StraightRows_Student_Package/data/"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip", help="path to a downloaded StraightRows_Student_Package.zip")
    args = parser.parse_args()
    if args.zip:
        blob = Path(args.zip).read_bytes()
    else:
        try:
            with urllib.request.urlopen(URL, timeout=120) as response:
                blob = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                sys.exit("The dataset has not been released yet. It is published at kickoff.")
            raise
    expected = (STARTER / "DATASET_SHA256").read_text().split()[0]
    actual = hashlib.sha256(blob).hexdigest()
    if actual != expected:
        sys.exit(f"Checksum mismatch: expected {expected}, got {actual}. Download the official release again.")
    target = STARTER / "data"
    count = 0
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        for name in archive.namelist():
            if not name.startswith(PREFIX) or name.endswith("/"):
                continue
            relative = Path(name[len(PREFIX):])
            if relative.is_absolute() or ".." in relative.parts:
                sys.exit(f"Unsafe path in archive: {name}")
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))
            count += 1
    print(f"Extracted {count} data files into {target}")


if __name__ == "__main__":
    main()
