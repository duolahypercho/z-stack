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

## Install

```bash
claude plugin marketplace add duolahypercho/z-stack
```

```bash
claude plugin install z-stack@z-stack
```

Then start a new session and run `/z-stack:evidence`.

## Layout

```text
.claude-plugin/marketplace.json     marketplace entry
plugins/z-stack/
  .claude-plugin/plugin.json
  skills/evidence/SKILL.md          the workflow
  skills/evidence/scripts/evidence.py   report builder
```

## License

MIT
