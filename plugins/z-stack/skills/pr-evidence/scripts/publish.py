#!/usr/bin/env python3
"""Push an evidence folder to the orphan branch z-stack-evidence, and print its raw URL.

The folder is pr-<n>/ once the PR exists, or branch-<name>/ before it does, so a PR can open
with its evidence already in the body. Never touches the PR branch or the working tree: the
commit is made in a temporary worktree.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BRANCH = "z-stack-evidence"
KEEP = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".md", ".json", ".html"}
MAX_BYTES = 40 * 1024 * 1024
README = """# Evidence for pull requests

Screenshots and charts that z-stack:pr-evidence made for this repository's pull requests,
one folder per PR (pr-<n>) or per branch when the evidence came before the PR (branch-<name>).
This branch has no code and is never merged.
"""


def git(*args, cwd=None, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, text=True, capture_output=True)


def repo_slug(root):
    out = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner"], cwd=root,
                         check=True, text=True, capture_output=True).stdout
    return json.loads(out)["nameWithOwner"]


def evidence_key(pr, branch, cwd=None):
    """pr-<n> once the PR exists, branch-<name> before it does. section.py names it the same way."""
    if pr is not None:
        if pr <= 0:
            raise ValueError("--pr must be a positive number")
        return f"pr-{pr}"
    name = branch or git("branch", "--show-current", cwd=cwd).stdout.strip()
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.")
    if not slug:
        raise ValueError("No PR and no branch checked out: pass --pr <n> or --branch <name>")
    return f"branch-{slug}"


def files_to_copy(folder):
    chosen = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in KEEP
              and not any(part.startswith(".") for part in p.relative_to(folder).parts)]
    total = sum(p.stat().st_size for p in chosen)
    if not chosen:
        raise ValueError(f"No images, markdown or json in {folder}")
    if total > MAX_BYTES:
        raise ValueError(f"Evidence is {total // 1024 // 1024} MB; keep it under {MAX_BYTES // 1024 // 1024} MB")
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, type=Path, help="Folder made by z-stack:evidence and/or chart.py")
    parser.add_argument("--pr", type=int, help="the PR number, once the PR exists")
    parser.add_argument("--branch", help="before the PR exists: its head branch (default: the current branch)")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--repo", help="owner/name; defaults to the current repository")
    args = parser.parse_args()
    folder = args.dir.resolve()
    try:
        root = Path(git("rev-parse", "--show-toplevel").stdout.strip())
        key = evidence_key(args.pr, args.branch, cwd=root)
        chosen = files_to_copy(folder)
        slug = args.repo or repo_slug(root)
    except (subprocess.CalledProcessError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(getattr(error, "stderr", None) or str(error))

    remote_has = git("ls-remote", "--exit-code", "--heads", args.remote, BRANCH, cwd=root, check=False).returncode == 0
    work = Path(tempfile.mkdtemp(prefix="z-stack-evidence-"))
    tree = work / "tree"
    scratch = f"{BRANCH}-new-{os.getpid()}"
    try:
        if remote_has:
            git("fetch", args.remote, f"{BRANCH}:refs/remotes/{args.remote}/{BRANCH}", cwd=root)
            git("worktree", "add", "--detach", str(tree), f"{args.remote}/{BRANCH}", cwd=root)
        else:
            git("worktree", "add", "--orphan", "-b", scratch, str(tree), cwd=root)
        target = tree / key
        if target.exists():
            shutil.rmtree(target)
        for path in chosen:
            dest = target / path.relative_to(folder)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
        (tree / "README.md").write_text(README)
        git("add", "-A", cwd=tree)
        if git("diff", "--cached", "--quiet", cwd=tree, check=False).returncode == 0:
            print("No change since the last publish.")
        else:
            git("commit", "-m", f"docs: evidence for {key}", cwd=tree)
            git("push", args.remote, f"HEAD:refs/heads/{BRANCH}", cwd=tree)
    except subprocess.CalledProcessError as error:
        print(f"git {' '.join(error.cmd[1:])} failed:\n{error.stderr}", file=sys.stderr)
        return 1
    finally:
        git("worktree", "remove", "--force", str(tree), cwd=root, check=False)
        git("branch", "-D", scratch, cwd=root, check=False)
        shutil.rmtree(work, ignore_errors=True)
    print(f"Published {len(chosen)} files")
    print(f"https://github.com/{slug}/raw/{BRANCH}/{key}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
