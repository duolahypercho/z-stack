#!/usr/bin/env python3
"""Print the PR's ## Evidence markdown from an evidence folder, with images on the z-stack-evidence branch."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

BRANCH = "z-stack-evidence"


def repo_slug():
    out = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner"],
                         check=True, text=True, capture_output=True).stdout
    return json.loads(out)["nameWithOwner"]


def screenshots(folder, url):
    manifest = folder / "manifest.json"
    if not manifest.is_file():
        return []
    data = json.loads(manifest.read_text())
    lines = ["### Screenshots", "", f"Before is `{data.get('base', 'base')}`, after is `{data.get('after', 'PR head')}`.", ""]
    for pair in data.get("pairs", []):
        changed = "n/a" if pair.get("changedPercent") is None else f'{pair["changedPercent"]:.2f}% of pixels changed'
        lines += [f"**{pair['name']}** · {changed}" + (f" · {pair['note']}" if pair.get("note") else ""), "",
                  "| Before | After |", "|---|---|",
                  f"| ![Before: {pair['name']}]({url}{pair['before']}) | ![After: {pair['name']}]({url}{pair['after']}) |", ""]
        if pair.get("diff"):
            lines += [f"<details><summary>Changed pixels</summary>\n\n![Diff: {pair['name']}]({url}{pair['diff']})\n\n</details>", ""]
    return lines


def charts(folder, url):
    summary = folder / "metrics.summary.json"
    if not summary.is_file():
        return []
    data = json.loads(summary.read_text())
    lines = ["### Measurements", ""]
    lines += [f"![{m['name']}]({url}{m['chart']})" for m in data.get("metrics", [])]
    table = folder / "metrics.md"
    if table.is_file():
        lines += ["", table.read_text().split("\n", 1)[1].strip()]
    return lines + [""]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", help="owner/name; defaults to the current repository")
    args = parser.parse_args()
    folder = args.dir.resolve()
    try:
        url = f"https://github.com/{args.repo or repo_slug()}/raw/{BRANCH}/pr-{args.pr}/"
        body = screenshots(folder, url) + charts(folder, url)
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as error:
        parser.error(str(error))
    if not body:
        parser.error(f"{folder} has neither manifest.json (screenshots) nor metrics.summary.json (charts)")
    print("\n".join(["## Evidence", "", "**What this shows:** _fill in, one line per change_", "",
                     "**Not shown:** _fill in_", ""] + body +
                    ["<sub>Made with [z-stack:pr-evidence](https://github.com/duolahypercho/z-stack).</sub>"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
