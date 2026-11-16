#!/usr/bin/env python3
"""Draw one before/after SVG per measured metric, plus metrics.md, from metrics.json. No dependencies."""
import argparse
import html
import json
import re
import statistics
import sys
from pathlib import Path

WIDTH, HEIGHT = 680, 178
LABEL_W, BAR_X, BAR_END = 76, 84, 548
ROW_Y = (70, 118)
BAR_H = 30


def samples(value, label):
    values = value if isinstance(value, list) else [value]
    if not values or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        raise ValueError(f"{label} must be a number or a non-empty list of numbers")
    return [float(v) for v in values]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "metric"


def fmt(value):
    if abs(value) >= 100:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def summarize(metric):
    name = metric.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Every metric needs a name")
    better = metric.get("better")
    if better not in ("lower", "higher"):
        raise ValueError(f"{name}: better must be 'lower' or 'higher'")
    before, after = samples(metric.get("before"), f"{name}.before"), samples(metric.get("after"), f"{name}.after")
    b_med, a_med = statistics.median(before), statistics.median(after)
    change = None if b_med == 0 else 100 * (a_med - b_med) / b_med
    spread = max(max(before) - min(before), max(after) - min(after))
    noise = abs(a_med - b_med) <= spread / 2 if len(before) > 1 and len(after) > 1 else a_med == b_med
    improved = (a_med < b_med) if better == "lower" else (a_med > b_med)
    verdict = "within noise" if noise else ("better" if improved else "worse")
    return dict(name=name, unit=metric.get("unit", ""), better=better, command=metric.get("command", ""),
                before=before, after=after, beforeMedian=b_med, afterMedian=a_med,
                changePercent=None if change is None else round(change, 1), verdict=verdict)


def svg(m):
    top = max(max(m["before"]), max(m["after"])) * 1.08 or 1.0
    x = lambda v: BAR_X + (BAR_END - BAR_X) * v / top
    tone = {"better": "good", "worse": "bad", "within noise": "flat"}[m["verdict"]]
    change = "n/a" if m["changePercent"] is None else f'{m["changePercent"]:+.1f}%'
    arrow = {"better": "▲ better", "worse": "▼ worse", "within noise": "≈ within noise"}[m["verdict"]]
    unit = f' · {html.escape(m["unit"])}' if m["unit"] else ""
    rows = []
    for (label, values, median, cls), y in zip(
            (("Before", m["before"], m["beforeMedian"], "b"), ("After", m["after"], m["afterMedian"], "a")), ROW_Y):
        rows.append(f'<text class="lab" x="{LABEL_W}" y="{y + 20}" text-anchor="end">{label}</text>')
        rows.append(f'<rect class="{cls}" x="{BAR_X}" y="{y}" width="{max(2, x(median) - BAR_X):.1f}" height="{BAR_H}" rx="5"/>')
        if len(values) > 1:
            lo, hi, mid = x(min(values)), x(max(values)), y + BAR_H / 2
            rows.append(f'<path class="rng" d="M{lo:.1f} {mid}H{hi:.1f}M{lo:.1f} {mid - 7}v14M{hi:.1f} {mid - 7}v14"/>')
        n = f" · n={len(values)}" if len(values) > 1 else ""
        rows.append(f'<text class="val" x="{max(x(median), x(max(values))) + 10:.1f}" y="{y + 20}">{fmt(median)}{n}</text>')
    title = html.escape(m["name"])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-label="{title}: before {fmt(m['beforeMedian'])}, after {fmt(m['afterMedian'])}, {change}, {m['verdict']}">
<style>
svg{{--bg:#FFFFFF;--ink:#16161A;--muted:#5E5E66;--line:#E4E4E7;--b:#A1A1AA;--a:#16161A;--good:#0A7A45;--bad:#C8321C;--flat:#5E5E66;font-family:-apple-system,"Segoe UI",system-ui,sans-serif}}
@media (prefers-color-scheme:dark){{svg{{--bg:#0D1117;--ink:#F0F0F0;--muted:#9BA1A9;--line:#30363D;--b:#545B64;--a:#E6E6E6;--good:#3FB97A;--bad:#FF6A4D;--flat:#9BA1A9}}}}
.bg{{fill:var(--bg);stroke:var(--line)}}.t{{fill:var(--ink);font-size:16px;font-weight:600}}.u{{fill:var(--muted);font-size:13px}}
.lab{{fill:var(--muted);font-size:13px}}.val{{fill:var(--ink);font-size:13px;font-variant-numeric:tabular-nums}}
.b{{fill:var(--b)}}.a{{fill:var(--a)}}.rng{{stroke:var(--muted);stroke-width:1.5;fill:none}}
.pill{{fill:var(--{tone});opacity:.14}}.chg{{fill:var(--{tone});font-size:13px;font-weight:600}}.axis{{stroke:var(--line)}}
</style>
<rect class="bg" x=".5" y=".5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="10"/>
<text class="t" x="20" y="34">{title}<tspan class="u">{unit} · {m['better']} is better</tspan></text>
<rect class="pill" x="{WIDTH - 196}" y="16" width="176" height="28" rx="14"/>
<text class="chg" x="{WIDTH - 108}" y="35" text-anchor="middle">{change} {arrow}</text>
<path class="axis" d="M{BAR_X} 60V{HEIGHT - 16}"/>
{chr(10).join(rows)}
</svg>
"""


def table(title, machine, metrics):
    lines = [f"### {title}", "", f"Measured on {machine}." if machine else "", "",
             "| Metric | Before (median) | After (median) | Change | Verdict | Runs | Range before → after |",
             "|---|---:|---:|---:|---|---:|---|"]
    for m in metrics:
        unit = f' {m["unit"]}' if m["unit"] else ""
        change = "n/a" if m["changePercent"] is None else f'{m["changePercent"]:+.1f}%'
        runs = f'{len(m["before"])} / {len(m["after"])}'
        rng = f'{fmt(min(m["before"]))}–{fmt(max(m["before"]))} → {fmt(min(m["after"]))}–{fmt(max(m["after"]))}'
        lines.append(f'| {m["name"]} | {fmt(m["beforeMedian"])}{unit} | {fmt(m["afterMedian"])}{unit} | {change} | {m["verdict"]} | {runs} | {rng} |')
    commands = [m for m in metrics if m["command"]]
    if commands:
        lines += ["", "How each number was measured:", ""] + [f'- {m["name"]}: `{m["command"]}`' for m in commands]
    return "\n".join(line for line in lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.metrics.read_text())
        raw = data.get("metrics")
        if not isinstance(raw, list) or not raw:
            raise ValueError("metrics.json needs a non-empty 'metrics' list")
        metrics = [summarize(m) for m in raw]
    except (OSError, ValueError, AttributeError) as error:
        parser.error(str(error))
    out = (args.out / "charts").resolve()
    out.mkdir(parents=True, exist_ok=True)
    seen = set()
    for m in metrics:
        name = slug(m["name"])
        if name in seen:
            parser.error(f"Two metrics named {m['name']!r}")
        seen.add(name)
        m["chart"] = f"charts/{name}.svg"
        (out / f"{name}.svg").write_text(svg(m))
        change = "n/a" if m["changePercent"] is None else f'{m["changePercent"]:+.1f}%'
        print(f'{m["name"]}: {fmt(m["beforeMedian"])} → {fmt(m["afterMedian"])} {m["unit"]} ({change}, {m["verdict"]})')
    title = data.get("title", "Measurements")
    (args.out / "metrics.md").write_text(table(title, data.get("machine", ""), metrics))
    (args.out / "metrics.summary.json").write_text(json.dumps(
        dict(title=title, machine=data.get("machine", ""), metrics=metrics), indent=2) + "\n")
    print(f"Charts: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
