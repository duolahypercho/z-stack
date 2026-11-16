# z-stack

Proof-first workflows for [Claude Code](https://claude.com/claude-code). Show the change, don't describe it.

## Skills

### `/z-stack:evidence`

Proves a change with before and after screenshots.

1. Finds the base ref (`HEAD` for uncommitted work, the merge-base for a branch).
2. Builds the **before** from a detached `git worktree`, so your working tree is never stashed or reset.
3. Captures the same screens, sizes and theme on both sides, using the project's own capture script when it has one (otherwise a browser, the iOS Simulator, or a Mac app screenshot).
4. Looks at every image and rejects blank or wrong frames.
5. Builds one `report.html` with side by side, a drag slider and a red pixel diff, plus a `manifest.json` with the sha256 of each image and the share of pixels changed.

The report generator also runs on its own:

```bash
python3 plugins/z-stack/skills/evidence/scripts/evidence.py \
  --out ./.evidence/my-change --title "New settings layout" --base main \
  --pair "settings-dark" before.png after.png "Groups moved into one column"
```

Pillow (`pip install pillow`) turns on the diff. Without it the report still builds.

### `/z-stack:pr-evidence`

Puts proof on a pull request, so a reviewer can trust it without checking out the branch.

- **Visible change:** before and after screenshots, made with `/z-stack:evidence`.
- **Change you measure** (speed, size, memory, failure rate): charts drawn from real runs on both sides. Every chart shows the median, the range of runs, the change in percent, and whether it moved the better way, the worse way, or stayed within noise. A regression is shown as plainly as a win.

The images go on an orphan branch, `z-stack-evidence`, one folder per PR, so the PR branch never carries them. The skill then writes an `## Evidence` section for the PR body.

```bash
python3 plugins/z-stack/skills/pr-evidence/scripts/chart.py metrics.json --out ./.evidence/pr-42
python3 plugins/z-stack/skills/pr-evidence/scripts/publish.py --dir ./.evidence/pr-42 --pr 42
python3 plugins/z-stack/skills/pr-evidence/scripts/section.py --dir ./.evidence/pr-42 --pr 42 > evidence.md
```

`metrics.json` holds the raw samples and the command that made them. See the skill for the format.

## Install

```bash
claude plugin marketplace add duolahypercho/z-stack
```

```bash
claude plugin install z-stack@z-stack
```

Then start a new session and run `/z-stack:evidence` or `/z-stack:pr-evidence`.

## Layout

```text
.claude-plugin/marketplace.json     marketplace entry
plugins/z-stack/
  .claude-plugin/plugin.json
  skills/evidence/SKILL.md          the workflow
  skills/evidence/scripts/evidence.py   report builder
  skills/pr-evidence/SKILL.md       proof on a PR
  skills/pr-evidence/scripts/       chart.py, publish.py, section.py
```

## License

MIT
