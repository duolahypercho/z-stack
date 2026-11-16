---
name: pr-evidence
description: "Put proof on a pull request: before and after screenshots for a visible change, or charts drawn from real measurements (timings, sizes, memory, test counts) for one you can't see. Hosts the images on an evidence branch and writes an Evidence section for the PR body or a comment. Use for /z-stack:pr-evidence, \"add evidence to the PR\", \"prove this PR\", \"show the numbers\", or before asking for review on a PR."
---

# z-stack:pr-evidence

A reviewer should be able to trust the PR from its Evidence section alone, without checking out the branch.

The section ends up with one of two kinds of proof, or both:

- **Screenshots**: the change is something a person sees.
- **Charts**: the change is something you measure, like speed, size, memory, a failure rate or test results.

## 1. Read the PR

1. Find the PR: `gh pr view --json number,url,baseRefName,headRefName,title,body`. No PR yet? Use the current branch against the main branch, and write the section so it can go into the PR description later.
2. `git diff --stat <base>...HEAD`. List what changed for a reviewer, as a person would put it.
3. Decide what kind of proof each change needs:

| The change | Proof |
|---|---|
| UI, layout, copy, theme, a new screen or state | Screenshots |
| Speed, startup, a query, a render loop | Chart of timings |
| Bundle or binary size, dependencies | Chart of sizes |
| Memory, leaks, CPU | Chart of samples over time or per run |
| A bug fix | A failing test before and a passing test after (output is enough) plus screenshots if it's visible |
| A pure refactor | Tests passing on both sides, and the same numbers before and after: a chart whose point is "no change" |

## 2. Screenshots

Follow the **z-stack:evidence** skill in full: before from a detached worktree at the merge-base, after from the PR head, with the same fixture, size and theme on both sides. It produces `before/`, `after/`, `diff/` and `manifest.json`. Keep 1 to 6 pairs, the ones that show the change most clearly.

## 3. Charts from real measurements

The numbers must come from runs you performed in this session. Never estimate, round up from memory, or invent a sample. When you can't measure, say so in the section and skip the chart.

1. Write down the command once, then run it on **both** sides: the before worktree and the PR head. Same machine, same build configuration (release vs debug), nothing heavy running in the background.
2. Repeat timing runs at least 5 times on each side, and discard a warm-up run when the first run is cold. Sizes and counts need one run.
3. Save the raw samples in `metrics.json`:

```json
{
  "title": "Cold launch got faster",
  "machine": "MacBook Pro M3, macOS 15.5, release build",
  "metrics": [
    {"name": "Cold launch", "unit": "ms", "better": "lower",
     "command": "scripts/perf.py --launch --runs 7",
     "before": [812, 798, 845, 801, 820, 809, 815],
     "after":  [541, 560, 538, 549, 552, 547, 544]},
    {"name": "App size", "unit": "MB", "better": "lower",
     "command": "du -sm dist/App.app", "before": 148, "after": 131}
  ]
}
```

   `better` is `lower` or `higher`. A metric can be one number or a list of samples.
4. Draw the charts:

```bash
python3 <this skill's base directory>/scripts/chart.py metrics.json --out <folder>
```

   It writes one SVG per metric: before and after bars at the median, the range of samples as a line, the change in percent, colored green when it moved the better way and red when it moved the worse way. It also writes `metrics.md`, a table with median, min, max and runs. Open every SVG with Read or a browser before using it.
5. A change smaller than the spread of the samples is noise. Say so ("within noise"), and don't call it a win.

## 4. Host the images

GitHub has no API for attaching images to a PR, so the images go on a branch of their own.

```bash
python3 <this skill's base directory>/scripts/publish.py --dir <folder> --pr <number>
```

It copies the folder to `z-stack-evidence/pr-<number>/` on an orphan branch named `z-stack-evidence` (made on first use, never merged), pushes that branch, and prints the image URLs. It never touches the PR branch or the working tree. Each run replaces that PR's folder.

Pushing is outward-facing. The person asking for PR evidence approves the push of the evidence branch. Ask first when the repository is public and the screenshots could show anything beyond synthetic data.

## 5. Write the Evidence section

```bash
python3 <this skill's base directory>/scripts/section.py --dir <folder> --pr <number> > evidence.md
```

It builds the markdown from the folder: a before | after table per screenshot pair with its note and changed pixels, each chart with its table, and how each number was measured (command and machine). Then add, in your own words at the top:

- **What this shows**: one line per change.
- **Not shown**: what the evidence doesn't cover (other sizes, real accounts, a slower machine, interaction).

Then deliver it:
- Show the person the section and the most telling image or chart first.
- With their go-ahead, put it on the PR. Either replace a previous `## Evidence` section in the body (`gh pr edit <n> --body-file`, keeping the rest of the body exactly as it was) or post it as a comment (`gh pr comment <n> --body-file evidence.md`). Prefer the body. Use a comment when the body belongs to someone else.
- Reply with the PR link and the table of results.

## Rules

- Before and after differ only in the code. A different machine, build mode, fixture or data set makes the comparison worthless. Redo it.
- Every chart has its command and machine in the section. A number with no way to reproduce it doesn't go in.
- A regression is shown as plainly as a win. Never leave out a metric because it got worse.
- No personal data in a screenshot or a sample: synthetic accounts, fixture content, no real tabs, mail or files.
