---
name: evidence
description: "Prove a change with before and after screenshots. Captures the same screen from the base ref (before) and the working tree (after), measures how many pixels changed, and builds one side-by-side report with a drag slider. Use for /z-stack:evidence, \"show me proof\", \"before and after\", \"screenshot the change\", or before handing back any change a person will look at."
---

# z-stack:evidence

Show the change. Do not describe it.

The deliverable is a folder with `before/`, `after/`, a `report.html` that puts each pair side by side, and a `manifest.json` that says exactly what was captured from which commit. The reply leads with the report, then a table of pairs.

## 1. Scope the change

1. Pick the base. Uncommitted work: `HEAD`. A branch: `git merge-base HEAD <main branch>`. The person can name another ref.
2. `git diff --stat <base>` (plus untracked files). Name the surfaces a person would see change: screens, states, sizes, light and dark.
3. Pick 1 to 6 pairs. Each pair is one surface in one state. Prefer the state that shows the change most directly over a tour of the app.
4. Nothing visible changed (a refactor, a pure backend fix)? Say so in one line, and give the evidence that does apply instead (a failing then passing test, a log line, a timing) as before and after output in the reply, and skip the screenshots.

## 2. Find the capture route

Use the first that fits. Read the project's README, AGENTS.md / CLAUDE.md and `scripts/` first: a project's own capture script beats anything generic.

| Project has | Capture with |
|---|---|
| Its own preview or screenshot script (`scripts/*preview*`, `*screenshot*`, `*capture*`) | That script, same flags for both sides |
| A web dev server (`.claude/launch.json`, `package.json` dev script) | `preview_start` + `computer` screenshot, or Playwright `page.screenshot` |
| A static page | Built-in browser `navigate` to the file, screenshot |
| An iOS app | iOS Simulator `screenshot` |
| A native Mac app with no preview mode | computer-use `app_screenshot` |

Same fixture, same window size, same appearance, same flags on both sides. Synthetic data only: never capture personal tabs, accounts, cookies or private files.

## 3. Capture before, then after

- **Before** comes from a detached worktree at the base: `git worktree add --detach <scratch>/before-src <base>`. Build and capture there. Never stash, reset or check out over the person's working tree.
- **After** comes from the working tree as it is.
- Builds are slow. Start both in the background at once, and write the plan or the report command while they run.
- Name files the same on both sides: `before/<pair>.png`, `after/<pair>.png`.
- Remove the worktree when done: `git worktree remove --force <scratch>/before-src`.

## 4. Look at every image

Open each capture with Read before building the report. A blank frame, the wrong screen, a loading spinner, a crash dialog, or a before and after that are byte-identical when the change should be visible: recapture, don't ship. Note in one line what each after image shows that the before does not.

## 5. Build the report

```bash
python3 <this skill's base directory>/scripts/evidence.py \
  --out <folder> --title "<change in a few words>" \
  --base <base ref> --after "working tree" \
  --pair "<pair-name>" <before.png> <after.png> "<what changed, one line>" \
  --pair ...
```

It copies the images in, writes `diff/<pair>.png` (changed pixels in red over a dimmed after), counts the changed pixels, and writes `report.html` (images embedded, one file, opens anywhere) and `manifest.json` (sha256 of every image, refs, sizes, changed %). Pillow gives the diff; without it the report still builds with no diff.

Where the folder goes:
- The project already keeps evidence somewhere (`docs/verification/`, `docs/evidence/`, `screenshots/`)? Follow that convention.
- Otherwise `.evidence/<YYYY-MM-DD>-<slug>/` in the repo, left out of git.
- Commit it only when the person asks.

## 6. Hand it over

1. `SendUserFile` the `report.html` (display `render`), and the most telling `after/` image.
2. Offer to publish the report as a private Artifact in one line, or publish it when the person said who will see it.
3. Reply, in this order:
   - The report path, as a link.
   - A table: pair · what changed · changed pixels.
   - **Verified:** what the images prove.
   - **Not verified:** what they don't (interaction, motion, other sizes, VoiceOver, real data). Screenshots of a synthetic fixture are not acceptance of the real flow. Say so.

## Rules

- Before and after differ in one thing: the code. If the fixture, size, theme or data differ, the pair proves nothing. Recapture.
- A 0.00% pair where a change was expected is a finding, not a pass.
- Never edit an image. Crop only with the same box on both sides, and say so in the pair's note.
