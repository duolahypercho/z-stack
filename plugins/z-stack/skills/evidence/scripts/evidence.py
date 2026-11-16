#!/usr/bin/env python3
"""Build a before/after evidence report: copies each pair, diffs it, writes report.html + manifest.json."""
import argparse
import base64
import hashlib
import html
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image, ImageChops
except ImportError:  # The report still builds; it just has no diff.
    Image = None

DIFF_THRESHOLD = 24  # Per-channel delta under this is antialiasing noise, not a change.
EMBED_LIMIT = 12 * 1024 * 1024  # Past this, link images instead of embedding them.


def slug(text):
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not value:
        raise ValueError(f"Pair name {text!r} has no letters or digits")
    return value


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diff_pair(before, after, out):
    """Changed pixels in red over a dimmed after image. Returns (changed %, note) or (None, reason)."""
    if Image is None:
        return None, "Pillow not installed"
    a = Image.open(before).convert("RGB")
    b = Image.open(after).convert("RGB")
    if a.size != b.size:
        return None, f"sizes differ ({a.size[0]}x{a.size[1]} vs {b.size[0]}x{b.size[1]})"
    delta = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v >= DIFF_THRESHOLD else 0)
    changed = sum(1 for v in delta.getdata() if v)
    base = Image.blend(b, Image.new("RGB", b.size, (0, 0, 0)), 0.65)
    red = Image.new("RGB", b.size, (255, 48, 48))
    Image.composite(red, base, delta).save(out)
    return round(100 * changed / (a.size[0] * a.size[1]), 2), None


def src(path, embed):
    if not embed:
        return html.escape(path.name if path.parent.name == "" else f"{path.parent.name}/{path.name}")
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def render(title, base, after_label, pairs, out, embed):
    rows = []
    for p in pairs:
        before, after = out / p["before"], out / p["after"]
        diff = out / p["diff"] if p.get("diff") else None
        changed = "n/a" if p["changedPercent"] is None else f'{p["changedPercent"]:.2f}%'
        diff_tab = (f'<button role="tab" data-view="diff">Diff</button>' if diff else "")
        diff_img = (f'<img class="v-diff" src="{src(diff, embed)}" alt="Changed pixels for {html.escape(p["name"])}">' if diff else "")
        rows.append(f"""
<section class="pair" aria-labelledby="h-{p['id']}">
  <header>
    <h2 id="h-{p['id']}">{html.escape(p['name'])}</h2>
    <span class="chg" data-zero="{str(p['changedPercent'] == 0).lower()}">{changed} changed</span>
  </header>
  {f'<p class="note">{html.escape(p["note"])}</p>' if p.get("note") else ""}
  <div class="tabs" role="tablist"><button role="tab" data-view="side" aria-selected="true">Side by side</button><button role="tab" data-view="slide">Slider</button>{diff_tab}</div>
  <div class="view" data-view="side">
    <figure class="v-side"><div><figcaption>Before · {html.escape(base)}</figcaption><img src="{src(before, embed)}" alt="Before"></div>
    <div><figcaption>After · {html.escape(after_label)}</figcaption><img src="{src(after, embed)}" alt="After"></div></figure>
    <div class="v-slide"><img src="{src(before, embed)}" alt="Before"><div class="top"><img src="{src(after, embed)}" alt="After"></div>
      <input type="range" min="0" max="100" value="50" aria-label="Reveal after image"><span class="lb">Before</span><span class="la">After</span></div>
    {diff_img}
  </div>
</section>""")
    page = TEMPLATE.replace("{{TITLE}}", html.escape(title)).replace("{{BASE}}", html.escape(base)) \
        .replace("{{AFTER}}", html.escape(after_label)).replace("{{WHEN}}", datetime.now().strftime("%Y-%m-%d %H:%M")) \
        .replace("{{COUNT}}", str(len(pairs))).replace("{{PAIRS}}", "".join(rows))
    (out / "report.html").write_text(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--base", required=True, help="Ref the before images came from")
    parser.add_argument("--after", default="working tree", help="What the after images came from")
    parser.add_argument("--pair", nargs="+", action="append", required=True, metavar="NAME BEFORE AFTER [NOTE]")
    args = parser.parse_args()

    out = args.out.resolve()
    for sub in ("before", "after", "diff"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    pairs, seen = [], set()
    for entry in args.pair:
        if len(entry) not in (3, 4):
            parser.error(f"--pair takes NAME BEFORE AFTER [NOTE], got {entry}")
        name, before_src, after_src = entry[0], Path(entry[1]), Path(entry[2])
        for path in (before_src, after_src):
            if not path.is_file():
                parser.error(f"{path} is not a file")
        pid = slug(name)
        if pid in seen:
            parser.error(f"Two pairs named {name!r}")
        seen.add(pid)
        ext = before_src.suffix.lower() or ".png"
        before, after = out / "before" / f"{pid}{ext}", out / "after" / f"{pid}{after_src.suffix.lower() or ext}"
        if before_src.resolve() != before:
            shutil.copyfile(before_src, before)
        if after_src.resolve() != after:
            shutil.copyfile(after_src, after)
        diff = out / "diff" / f"{pid}.png"
        percent, reason = diff_pair(before, after, diff)
        pair = dict(id=pid, name=name, note=entry[3] if len(entry) == 4 else "",
                    before=str(before.relative_to(out)), after=str(after.relative_to(out)),
                    beforeSHA256=sha256(before), afterSHA256=sha256(after),
                    identical=sha256(before) == sha256(after), changedPercent=percent)
        if percent is not None:
            pair["diff"] = str(diff.relative_to(out))
        else:
            pair["diffSkipped"] = reason
        pairs.append(pair)
        flag = " (IDENTICAL FILES)" if pair["identical"] else ""
        print(f"{name}: {'n/a (' + reason + ')' if percent is None else f'{percent:.2f}%'} changed{flag}")

    size = sum((out / p[k]).stat().st_size for p in pairs for k in ("before", "after", "diff") if p.get(k))
    render(args.title, args.base, args.after, pairs, out, embed=size <= EMBED_LIMIT)
    manifest = dict(title=args.title, base=args.base, after=args.after,
                    createdAt=datetime.now(timezone.utc).isoformat(),
                    diffThreshold=DIFF_THRESHOLD, embedded=size <= EMBED_LIMIT, pairs=pairs)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Report: {out / 'report.html'}")
    return 0


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidence · {{TITLE}}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap">
<style>
:root{--bg:#F6F5F2;--panel:#FFF;--ink:#16161A;--muted:#5E5E66;--line:rgba(22,22,26,.12);--accent:#D9361E;--ok:#0A7A45;
--sans:"Geist",ui-sans-serif,-apple-system,system-ui,sans-serif;--mono:"Geist Mono",ui-monospace,Menlo,monospace;--ease:cubic-bezier(.16,1,.3,1)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0E0E10;--panel:#17171A;--ink:#F2F2F0;--muted:#A0A0A8;--line:rgba(242,242,240,.12);--accent:#FF5A3C;--ok:#2BC77A}}
:root[data-theme="dark"]{--bg:#0E0E10;--panel:#17171A;--ink:#F2F2F0;--muted:#A0A0A8;--line:rgba(242,242,240,.12);--accent:#FF5A3C;--ok:#2BC77A}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 var(--sans)}
main{max-width:1440px;margin:0 auto;padding:clamp(24px,4vw,56px) 16px 80px}
.mast{display:grid;gap:6px;border-bottom:2px solid var(--ink);padding-bottom:20px;margin-bottom:36px}
.kicker{font:500 12px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
h1{font:600 clamp(28px,1rem + 3vw,52px)/1.05 var(--sans);letter-spacing:-.02em;margin:0}
.meta{font:13px var(--mono);color:var(--muted)}
.pair{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:28px;box-shadow:0 1px 0 rgba(0,0,0,.03),0 12px 32px -20px rgba(0,0,0,.25)}
.pair header{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
h2{margin:0;font:600 19px var(--sans)}.note{margin:6px 0 14px;color:var(--muted)}
.chg{font:500 12px var(--mono);padding:3px 9px;border-radius:99px;background:color-mix(in oklab,var(--accent) 14%,transparent);color:var(--accent)}
.chg[data-zero="true"]{background:color-mix(in oklab,var(--ok) 14%,transparent);color:var(--ok)}
.tabs{display:flex;gap:4px;margin:10px 0 14px}
.tabs button{font:500 13px var(--sans);color:var(--muted);background:none;border:1px solid transparent;border-radius:8px;padding:5px 11px;cursor:pointer;transition:background .15s var(--ease)}
.tabs button:hover{background:var(--line)}.tabs button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tabs button[aria-selected="true"]{color:var(--ink);border-color:var(--line);background:var(--bg)}
.view>*{display:none}.view[data-view="side"] .v-side,.view[data-view="slide"] .v-slide,.view[data-view="diff"] .v-diff{display:grid}
.v-side{grid-template-columns:1fr 1fr;gap:14px;margin:0}.v-side div{min-width:0}
figcaption{font:500 12px var(--mono);color:var(--muted);margin-bottom:6px}
img{max-width:100%;height:auto;display:block;border-radius:8px;border:1px solid var(--line)}
.v-slide{position:relative;max-width:1100px}.v-slide>img{width:100%}
.v-slide .top{position:absolute;inset:0;clip-path:inset(0 0 0 50%)}.v-slide .top img{width:100%}
.v-slide input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:ew-resize;margin:0}
.v-slide .lb,.v-slide .la{position:absolute;top:10px;font:500 11px var(--mono);background:var(--ink);color:var(--bg);padding:2px 7px;border-radius:5px;pointer-events:none}
.v-slide .lb{left:10px}.v-slide .la{right:10px}
@media (max-width:760px){.v-side{grid-template-columns:1fr}}
</style></head><body><main>
<header class="mast"><span class="kicker">z-stack:evidence</span><h1>{{TITLE}}</h1>
<span class="meta">before {{BASE}} → after {{AFTER}} · {{COUNT}} pair(s) · {{WHEN}}</span></header>
{{PAIRS}}
</main><script>
document.querySelectorAll('.pair').forEach(function(pair){
  var view=pair.querySelector('.view');
  pair.querySelectorAll('.tabs button').forEach(function(b){b.addEventListener('click',function(){
    pair.querySelectorAll('.tabs button').forEach(function(x){x.setAttribute('aria-selected',x===b)});
    view.dataset.view=b.dataset.view;});});
  var range=pair.querySelector('input[type=range]'),top=pair.querySelector('.top');
  range.addEventListener('input',function(){top.style.clipPath='inset(0 0 0 '+range.value+'%)';});
});
</script></body></html>"""

if __name__ == "__main__":
    sys.exit(main())
