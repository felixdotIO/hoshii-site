#!/usr/bin/env python3
"""Fail if any internal link does not resolve, or is not root-relative.

Every page is a directory index (`pricing/index.html`, served at `/pricing/`)
and every internal link is root-relative and extensionless. Both halves of that
have to hold or the site breaks in ways that are easy to miss:

- A relative link on an extensionless URL resolves differently depending on
  whether the visitor's URL carried a trailing slash, so `/policies/imprint`
  and `/policies/imprint/` would send `../privacy-policy/` to two places. Any
  relative internal link is therefore an error, not a style choice.
- A link to a page that no longer exists is a 404 the generator cannot see,
  because it does not know what the other pages emitted.

Checked against the files on disk rather than a running server, so it works in
CI with nothing started.

    python3 tools/check-links.py     # exit 0 clean, 1 on any failure
"""

import glob
import os
import posixpath
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTERNAL = ("http://", "https://", "//", "mailto:", "tel:", "data:")


def pages():
    """Every real page, newest layout: <dir>/index.html. Scratch files skipped."""
    found = []
    for pattern in ("index.html", "*/index.html", "*/*/index.html"):
        for path in glob.glob(os.path.join(ROOT, pattern)):
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if any(part.startswith("_") for part in rel.split("/")):
                continue
            found.append(rel)
    return sorted(set(found))


def url_of(rel_path):
    d = posixpath.dirname(rel_path)
    return "/" + (d + "/" if d else "")


def file_for(url):
    """The file a root-relative URL is served from, or None."""
    target = url.lstrip("/")
    candidates = [target]
    if url.endswith("/") or not target:
        candidates = [posixpath.join(target, "index.html")]
    for c in candidates:
        full = os.path.join(ROOT, c.replace("/", os.sep))
        if os.path.isfile(full):
            return c
    return None


def main():
    ids, problems = {}, []
    all_pages = pages()
    if not all_pages:
        sys.exit("check-links: found no pages, which cannot be right")

    for rel in all_pages:
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        ids[url_of(rel)] = set(re.findall(r'\sid="([^"]+)"', text))

    checked = 0
    for rel in all_pages:
        own = url_of(rel)
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        # href and src are the obvious ones. srcset carries the AVIF sources and
        # style="--shot: url(...)" carries the panel photographs; both were
        # missed once, and both failed quietly -- <picture> falls back to the
        # JPG, so nine 404s showed nothing on the page at all.
        found = [(a, v) for a, v in re.findall(r'\b(href|src)="([^"]*)"', text)]
        for val in re.findall(r'\bsrcset="([^"]*)"', text):
            for part in val.split(","):
                bits = part.strip().split(None, 1)
                if bits:
                    found.append(("srcset", bits[0]))
        for val in re.findall(r'\bstyle="([^"]*)"', text):
            for _, url in re.findall(r"url\((['\"]?)([^)'\"]+)\1\)", val):
                found.append(("style url()", url))

        for attr, val in found:
            if not val or val.startswith(EXTERNAL):
                continue
            if val.startswith("#"):
                if val != "#" and val[1:] not in ids[own]:
                    problems.append(f"{rel}: anchor {val} has no matching id on the page")
                continue
            if not val.startswith("/"):
                problems.append(
                    f"{rel}: {attr}=\"{val}\" is relative. Internal links must be "
                    f"root-relative, because extensionless URLs make relative "
                    f"paths depend on the trailing slash."
                )
                continue
            checked += 1
            path, _, frag = val.partition("#")
            path = path.split("?")[0]
            if file_for(path) is None:
                problems.append(f"{rel}: {attr}=\"{val}\" resolves to nothing on disk")
            elif frag and path in ids and frag not in ids[path]:
                problems.append(f"{rel}: {val} points at an id {path} does not have")

    if problems:
        print(f"{len(problems)} link problem(s) across {len(all_pages)} pages:\n")
        for p in problems:
            print(f"  {p}")
        return 1

    print(f"{len(all_pages)} pages, {checked} internal links, all resolve and all root-relative")
    return 0


if __name__ == "__main__":
    sys.exit(main())
