#!/usr/bin/env python3
"""Write the shell of a z-stack:ui-demo page.

One self-contained HTML file: an option switcher, a trade-off note per option,
light and dark, a stage drawn at the app's window size, and a Pick panel.
Each option gets an empty render function to fill in by hand.
"""
import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.html")
MIN_OPTIONS, MAX_OPTIONS = 2, 4
MAX_BASELINE_BYTES = 4 * 1024 * 1024
DEFAULT_SANS = 'ui-sans-serif, -apple-system, "SF Pro Text", system-ui, sans-serif'
DEFAULT_SUBTITLE = "Click through each option, try light and dark, then pick the one to build."
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
THEMES = {"both": ["dark", "light"], "dark": ["dark"], "light": ["light"]}


def fail(message):
    sys.exit(f"scaffold: {message}")


def parse_option(text):
    """`a|Short name|The idea in one sentence.`"""
    parts = [part.strip() for part in text.split("|")]
    if len(parts) != 3 or not all(parts):
        fail(f"--option must be 'id|name|idea', got {text!r}")
    option_id, name, idea = parts
    if not re.fullmatch(r"[a-z]", option_id):
        fail(f"option id must be one lower-case letter (a, b, c, d), got {option_id!r}")
    return {"id": option_id, "name": name, "idea": idea, "points": [], "cost": ""}


def parse_size(text):
    match = re.fullmatch(r"(\d{3,4})x(\d{3,4})", text.lower().replace("×", "x"))
    if not match:
        fail(f"--size must look like 1100x660, got {text!r}")
    return {"w": int(match[1]), "h": int(match[2])}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "demo"


def js_literal(value):
    """JSON is valid JS; break `</` so the data can't close the script tag."""
    return json.dumps(value, indent=2, ensure_ascii=False).replace("</", "<\\/")


def js_template_text(text):
    """Text safe inside a JS template literal that becomes HTML."""
    return html.escape(text).replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def render_stub(option):
    letter = option["id"].upper()
    one_line = " ".join(f"{option['name']}: {option['idea']}".split())
    return (
        f"// Option {letter} · {one_line}\n"
        f"function render_{option['id']}() {{\n"
        f"  return `<div class=\"todo\" data-todo>{letter} · {js_template_text(option['name'])}"
        f"<small>Draw this option in render_{option['id']}()</small></div>`;\n"
        f"}}"
    )


def baseline_js(path):
    if path is None:
        return ""
    if not path.is_file():
        fail(f"--baseline {path} not found")
    mime = IMAGE_TYPES.get(path.suffix.lower())
    if mime is None:
        fail(f"--baseline must be one of {', '.join(IMAGE_TYPES)}, got {path.suffix}")
    data = path.read_bytes()
    if len(data) > MAX_BASELINE_BYTES:
        fail(f"--baseline is {len(data) // 1024} KB; keep it under {MAX_BASELINE_BYTES // 1024} KB (capture at 1x or crop)")
    encoded = base64.b64encode(data).decode("ascii")
    return (
        "\n// Today: the current screen, captured before any option was drawn.\n"
        f'const BASELINE = "data:{mime};base64,{encoded}";\n'
        "function render_today() {\n"
        '  return `<img class="baseline" src="${BASELINE}" alt="Today: the current screen">`;\n'
        "}\n"
    )


def font_parts(font):
    if not font:
        return "", DEFAULT_SANS
    if not re.fullmatch(r"[A-Za-z0-9 ]{2,40}", font):
        fail(f"--font must be a Google Fonts family name, got {font!r}")
    family = font.strip().replace(" ", "+")
    link = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={family}:wght@400;500;600&display=swap">'
    )
    return link, f'"{font.strip()}", {DEFAULT_SANS}'


def build(args):
    options = [parse_option(text) for text in args.option]
    if not MIN_OPTIONS <= len(options) <= MAX_OPTIONS:
        fail(f"give {MIN_OPTIONS} to {MAX_OPTIONS} --option values, got {len(options)}")
    ids = [option["id"] for option in options]
    if len(set(ids)) != len(ids):
        fail(f"option ids repeat: {ids}")
    if args.recommend:
        if args.recommend not in ids:
            fail(f"--recommend {args.recommend!r} is not one of {ids}")
        for option in options:
            option["recommended"] = option["id"] == args.recommend

    all_options = list(options)
    if args.baseline:
        all_options.insert(0, {"id": "today", "name": "Today", "idea": "What ships now.",
                               "points": [], "cost": "Nothing to build."})

    font_link, sans = font_parts(args.font)
    size = parse_size(args.size)
    demo = {"title": args.title, "slug": slugify(args.title), "size": size, "themes": THEMES[args.themes]}
    render_map = ", ".join(f"{option['id']}: render_{option['id']}" for option in all_options)

    replacements = {
        "{{NAME}}": html.escape(args.name or args.title),
        "{{TITLE}}": html.escape(args.title),
        "{{SUBTITLE}}": html.escape(args.subtitle),
        "{{FONT_LINK}}": font_link,
        "{{SANS}}": sans,
        "{{W}}": str(size["w"]),
        "{{H}}": str(size["h"]),
        "{{DEMO_JSON}}": js_literal(demo),
        "{{OPTIONS_JSON}}": js_literal(all_options),
        "{{BASELINE_JS}}": baseline_js(args.baseline),
        "{{RENDERS}}": "\n\n".join(render_stub(option) for option in options),
        "{{RENDER_MAP}}": render_map,
    }
    page = TEMPLATE.read_text()
    for marker, value in replacements.items():
        page = page.replace(marker, value)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if leftover:
        fail(f"template markers left unfilled: {sorted(set(leftover))}")
    return page, options


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, type=Path, help="the .html file to write")
    parser.add_argument("--title", required=True, help="the open question, as the page heading")
    parser.add_argument("--name", help="2 to 4 word page title for the browser tab (default: --title)")
    parser.add_argument("--subtitle", default=DEFAULT_SUBTITLE)
    parser.add_argument("--option", action="append", default=[], metavar="ID|NAME|IDEA",
                        help="one per option, 2 to 4, e.g. 'a|Sidebar swaps|The sidebar turns into the page list.'")
    parser.add_argument("--recommend", metavar="ID", help="the option you recommend")
    parser.add_argument("--size", default="1100x660", help="window size the options are drawn at")
    parser.add_argument("--themes", choices=sorted(THEMES), default="both")
    parser.add_argument("--font", help="Google Fonts family the project uses, e.g. Geist")
    parser.add_argument("--baseline", type=Path, help="screenshot of the screen today, shown first as 'Today'")
    parser.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = parser.parse_args()

    if args.out.suffix.lower() != ".html":
        fail("--out must end in .html")
    if args.out.exists() and not args.force:
        fail(f"{args.out} exists. Make a new round (<slug>-r2.html) or pass --force")

    page, options = build(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page)

    stubs = ", ".join(f"render_{option['id']}()" for option in options)
    print(f"wrote {args.out} ({len(page) // 1024} KB, {len(options)} options)")
    print(f"next: draw {stubs}; fill points and cost in OPTIONS; swap the placeholder tokens for the project's")
    print(f"done when: grep -c data-todo {args.out} prints 0")


if __name__ == "__main__":
    main()
