# z-stack

Proof-first workflows for [Claude Code](https://claude.com/claude-code). Show the options before building, then show the change, don't describe it.

## Skills

### `/z-stack:ui-demo`

Mocks up a UI change before any product code is touched, as one demo site with every design side by side, so people pick the design instead of reading about it.

1. Frames one open question and 2 to 4 options that differ in structure or behavior, each with trade-offs and a build cost in hours or days.
2. Draws every option live, with the project's own tokens, copy and window size, next to screenshots of the screen today in each theme.
3. Builds one site with three views over the same designs: **All side by side** with a "How they differ" table, **Compare two** side by side or with a slider, and **One at a time**. One click opens the same panel in every design at once.
4. Makes every design a working prototype with an interaction kit (`data-toggle`, `data-set`, `data-bind`, `data-busy`, `data-toast`): menus, dialogs, tabs, typing, loading and toasts work with no code. Scenarios (Typical, Empty, Error) flip every design at once, and `?audit=1` outlines any control that does nothing.
5. Opens the site live in the browser pane, and checks every view in light and dark, and at phone width, before anyone sees it.
6. Lets people choose: a question in the chat for one person, or a private Artifact with shared picks for a team.
7. Iterates in rounds (`<slug>-r2.html`), then writes the pick down in `<slug>.decision.md` as the build brief.

The site shell and the local server also run on their own:

```bash
python3 plugins/z-stack/skills/ui-demo/scripts/scaffold.py \
  --out docs/demos/settings-layout.html --title "Where Settings opens" \
  --option "a|Sidebar swaps|The sidebar turns into the Settings list." \
  --option "b|Tab with header|Settings opens in the card like any tab." \
  --recommend a --baseline-dark today-dark.png --baseline-light today-light.png
```

```bash
python3 -I plugins/z-stack/skills/ui-demo/scripts/serve.py "$PWD/docs/demos"
```

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

Then start a new session and run `/z-stack:ui-demo`, `/z-stack:evidence` or `/z-stack:pr-evidence`.

## Layout

```text
.claude-plugin/marketplace.json     marketplace entry
plugins/z-stack/
  .claude-plugin/plugin.json
  skills/ui-demo/SKILL.md           options to pick from, before building
  skills/ui-demo/scripts/           scaffold.py, template.html, serve.py
  skills/evidence/SKILL.md          the workflow
  skills/evidence/scripts/evidence.py   report builder
  skills/pr-evidence/SKILL.md       proof on a PR
  skills/pr-evidence/scripts/       chart.py, publish.py, section.py
```

## License

MIT
