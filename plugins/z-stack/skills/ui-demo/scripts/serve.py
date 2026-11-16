#!/usr/bin/env python3
"""Serve one ui-demo folder on 127.0.0.1, so the browser pane opens it as a live site.

Run it with -I and an absolute folder, so Python never reads the current directory
(a launcher may start it somewhere it can't read):

    python3 -I serve.py /abs/path/to/docs/demos [--port 8790]

The port defaults to $PORT when a launcher sets one, else 8790.
"""
import argparse
import functools
import http.server
import os
import sys
from pathlib import Path

DEFAULT_PORT = 8790


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path, help="absolute path of the folder that holds the demo")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    args = parser.parse_args()

    if not args.folder.is_absolute():
        sys.exit(f"serve: pass an absolute folder, got {args.folder}")
    if not args.folder.is_dir():
        sys.exit(f"serve: {args.folder} is not a folder")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.folder))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"serving {args.folder} at http://127.0.0.1:{args.port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
