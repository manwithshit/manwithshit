#!/usr/bin/env python3
"""Refresh the stats line between <!--stats:start--> and <!--stats:end-->.

Counts only public, non-fork repositories owned by USER, and excludes the
profile repository itself (USER/USER) so the number matches what a visitor
would call "projects".

Run locally with no token (60 req/h, enough), or in Actions with GITHUB_TOKEN.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

USER = os.environ.get("PROFILE_USER", "manwithshit")
FILES = {
    "README.md": "{n} projects · {s} stars · {when_en}",
    "README.zh-CN.md": "{n} 个项目 · {s} star · {when_zh}",
}
START, END = "<!--stats:start-->", "<!--stats:end-->"


def api(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "profile-stats",
        "Accept": "application/vnd.github+json",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_repos():
    repos, page = [], 1
    while page <= 10:
        batch = api(f"https://api.github.com/users/{USER}/repos"
                    f"?per_page=100&page={page}&type=owner")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    return [r for r in repos
            if not r["fork"] and not r["private"] and r["name"] != USER]


def main():
    try:
        repos = fetch_repos()
    except urllib.error.HTTPError as e:
        print(f"GitHub API failed ({e.code}); leaving the stats line untouched.")
        return 0

    if not repos:
        print("No repositories returned; leaving the stats line untouched.")
        return 0

    n = len(repos)
    s = sum(r["stargazers_count"] for r in repos)
    years = {r["created_at"][:4] for r in repos}
    lo, hi = min(years), max(years)

    if lo == hi:
        when_en, when_zh = f"all built in {lo}", f"全部建于 {lo} 年"
    else:
        when_en, when_zh = f"building since {lo}", f"自 {lo} 年起"

    values = {"n": n, "s": f"{s:,}", "when_en": when_en, "when_zh": when_zh}
    changed = []

    for name, template in FILES.items():
        if not os.path.exists(name):
            continue
        old = open(name, encoding="utf-8").read()
        line = template.format(**values)
        new = re.sub(
            re.escape(START) + r".*?" + re.escape(END),
            START + line + END,
            old,
            flags=re.S,
        )
        if new != old:
            open(name, "w", encoding="utf-8").write(new)
            changed.append(name)
        print(f"{name}: {line}")

    print("changed: " + (", ".join(changed) if changed else "nothing"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
