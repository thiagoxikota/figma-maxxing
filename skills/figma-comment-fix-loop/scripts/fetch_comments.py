#!/usr/bin/env python3
"""Save the raw comments of one Figma file to a JSON file.

Usage: python3 fetch_comments.py <fileKey> [output.json]

Reads the personal access token from the FIGMA_ACCESS_TOKEN environment
variable and sends it only to api.figma.com. The token is never printed,
logged or written to disk. Standard library only.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.figma.com/v1/files/{key}/comments"
FILE_KEY = re.compile(r"^[0-9A-Za-z]{10,128}$")


def main(argv):
    if len(argv) not in (2, 3) or not FILE_KEY.match(argv[1]):
        print("usage: fetch_comments.py <fileKey> [output.json]", file=sys.stderr)
        return 2
    token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
    if not token:
        print("FIGMA_ACCESS_TOKEN is not set in this shell. Export it, then run again.", file=sys.stderr)
        return 2
    out = argv[2] if len(argv) == 3 else "comments-raw.json"
    req = urllib.request.Request(API.format(key=argv[1]), headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as err:
        hints = {
            403: "the token lacks the comments scope, or it cannot see this file",
            404: "the file belongs to an account this token cannot read; ask the user to paste the comments",
            429: "rate limited; wait before retrying and do not loop",
        }
        print(f"Figma API returned {err.code}: {hints.get(err.code, 'see the response body')}", file=sys.stderr)
        return 1
    except urllib.error.URLError as err:
        print(f"Network error: {err.reason}", file=sys.stderr)
        return 1
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    comments = data.get("comments", [])
    open_count = sum(1 for c in comments if not c.get("resolved_at"))
    print(f"{len(comments)} comments saved to {out} ({open_count} open)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
