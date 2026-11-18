#!/usr/bin/env python3
"""Resolve the official release and third-party branch heads once per run."""
import html.parser
import json
import os
import re
import subprocess
import sys
import urllib.request

RELEASES = "https://downloads.immortalwrt.org/releases/"
SOURCE = "https://github.com/immortalwrt/immortalwrt.git"
PACKAGES = {
    "aurora": ("eamonxg/luci-theme-aurora", "master"),
    "aurora-config": ("eamonxg/luci-app-aurora-config", "master"),
    "nikki": ("nikkinikki-org/OpenWrt-nikki", "main"),
    "openclash": ("vernesong/OpenClash", "master"),
    "momo": ("nikkinikki-org/OpenWrt-momo", "main"),
    "fastfetch-openwrt": ("ntbowen/fastfetch-openwrt", "main"),
    "luci-app-poweroffdevice": ("sirpdboy/luci-app-poweroffdevice", "master"),
    "luci-app-tailscale": ("asvow/luci-app-tailscale", "main"),
    "luci-app-easytier": ("EasyTier/luci-app-easytier", "main"),
    "turboacc": ("mufeng05/turboacc", "main"),
}


class DirectoryParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.versions = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            match = re.fullmatch(r"(?:\./)?(\d+\.\d+\.\d+)/", href)
            if match:
                self.versions.add(match.group(1))


def latest_version(page):
    parser = DirectoryParser()
    parser.feed(page)
    if not parser.versions:
        raise ValueError("No stable release directories found")
    return max(parser.versions, key=lambda x: tuple(map(int, x.split("."))))


def resolve_ref(repo, ref):
    result = subprocess.run(
        ["git", "ls-remote", repo, ref, ref + "^{}"],
        check=True, capture_output=True, text=True, timeout=60,
    )
    refs = dict(line.split() for line in result.stdout.splitlines())
    # ls-remote outputs SHA then ref; prefer the peeled annotated tag.
    refs = {refname: sha for sha, refname in refs.items()}
    sha = refs.get(ref + "^{}") or refs.get(ref)
    if not sha or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError(f"Cannot resolve {repo} {ref}")
    return sha


def main():
    proxy = os.environ.get("WRT_PROXY", "nikki")
    if proxy not in ("nikki", "openclash", "momo"):
        raise ValueError(f"Unsupported proxy {proxy}")
    with urllib.request.urlopen(RELEASES, timeout=30) as response:
        version = latest_version(response.read().decode("utf-8"))
    tag = "v" + version
    commit = resolve_ref(SOURCE, "refs/tags/" + tag)
    packages = {}
    for name, (repo, branch) in PACKAGES.items():
        if name in ("nikki", "openclash", "momo") and name != proxy:
            continue
        sha = resolve_ref("https://github.com/" + repo + ".git", "refs/heads/" + branch)
        packages[name] = {"repo": repo, "branch": branch, "commit": sha}
    lock = {"version": version, "tag": tag, "commit": commit,
            "proxy": proxy, "packages": packages}
    output = json.dumps(lock, separators=(",", ":"))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write("lock=" + output + "\n")
    print(output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Source resolution failed: {exc}", file=sys.stderr)
        sys.exit(1)
