#!/usr/bin/env python3
"""Reject moving feeds and verify their checked-out commits."""
import pathlib
import re
import subprocess
import sys


def parse_feeds(text):
    feeds = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 3 or parts[0] != "src-git":
            raise ValueError(f"Unsupported feed: {line}")
        match = re.fullmatch(r"https://[^\s^]+\.git\^([0-9a-f]{40})", parts[2])
        if not match or not re.fullmatch(r"[A-Za-z0-9_-]+", parts[1]) or parts[1] in feeds:
            raise ValueError(f"Feed is not uniquely pinned to a commit: {line}")
        feeds[parts[1]] = match.group(1)
    if not feeds:
        raise ValueError("No pinned feeds found")
    return feeds


def main():
    root = pathlib.Path(sys.argv[1])
    feeds = parse_feeds((root / "feeds.conf.default").read_text())
    for name, expected in feeds.items():
        actual = subprocess.check_output(
            ["git", "-C", str(root / "feeds" / name), "rev-parse", "HEAD"], text=True
        ).strip()
        if actual != expected:
            raise ValueError(f"{name}: expected {expected}, got {actual}")
        print(f"{name} {actual}")


if __name__ == "__main__":
    main()
