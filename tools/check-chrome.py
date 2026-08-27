#!/usr/bin/env python3
"""Fail if index.html's nav or footer has drifted from the generator's.

index.html is the one page gen-legal.py does not emit, so its header and footer
are a hand-maintained copy of FULL_HEADER and PAGE's footer. Nothing stopped the
two diverging, and they had: the homepage was the only page whose footer linked
to faq.html, and it sat in a different column position. This makes that class of
drift a build failure instead of something you notice months later.

Both sides are run through the generator's own clean_urls first, so the
comparison is between two sets of root-relative extensionless URLs. There is
one way to write any target. Exactly one equivalence is forgiven, because it is
real: the homepage's `#product` scrolls where a subpage's `/#product` has to
navigate. Everything else -- link sets, order, markup, attributes -- must match.

    python3 tools/check-chrome.py     # exit 0 clean, 1 on drift
"""

import difflib
import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_generator():
    spec = importlib.util.spec_from_file_location("gen", ROOT / "tools" / "gen-legal.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def normalise(text, gen):
    """Both sides through the generator's own link rewriter, then compared.

    Every page's links are root-relative and extensionless, so there is exactly
    one way to write any given target and no path-style differences left to
    forgive. The templates still hold relative paths; clean_urls resolves them
    the same way it does at build time.
    """
    text = gen.clean_urls(text, ".")
    # The one legitimate difference, and the only one allowed: on the homepage
    # a same-page anchor is `#product`, which scrolls. The generated subpages
    # need `/#product`, which navigates. Both are correct for their own page,
    # so they compare equal here and nothing else does.
    text = text.replace('href="/#product"', 'href="#product"')
    return [l.rstrip() for l in text.strip().split("\n")]


def extract(source, pattern, what):
    m = re.search(pattern, source, re.S)
    if not m:
        sys.exit(f"check-chrome: could not find the {what} to compare")
    return m.group(0)


def main():
    gen = load_generator()
    index = (ROOT / "index.html").read_text(encoding="utf-8")

    expected_footer = (
        extract(gen.PAGE, r'<footer class="foot">.*?</footer>', "generator footer")
        .replace("{up}", ".")
        .replace("{dm}", "")
        .replace("{lg}", "policies/")
    )

    checks = [
        (
            "header",
            gen.FULL_HEADER.format(up=".", dm="", cta="Book a demo"),
            extract(index, r'    <header class="titlebar">.*?</header>\n', "index header"),
        ),
        (
            "footer",
            expected_footer,
            extract(index, r'<footer class="foot">.*?</footer>', "index footer"),
        ),
    ]

    failed = False

    # CSS_V is bumped in the generator, but index.html carries its own copy of
    # the query string because it is not generated. The two went out of step
    # once already; when they do, the homepage serves stale CSS while every
    # other page picks up the new file, which looks like a rendering bug
    # anywhere except where the cause is.
    stamped = set(re.findall(r'styles\.css\?v=(\d+)', index))
    if stamped != {gen.CSS_V}:
        failed = True
        print(
            f"\nindex.html asks for styles.css?v={','.join(sorted(stamped)) or '(none)'} "
            f"but gen-legal.py's CSS_V is {gen.CSS_V}.\n"
            "Bump the query string in index.html to match, or CSS_V to match it."
        )
    else:
        print(f"css version: in step with the generator (v={gen.CSS_V})")

    for name, expected, got in checks:
        diff = list(
            difflib.unified_diff(
                normalise(expected, gen),
                normalise(got, gen),
                f"gen-legal.py ({name})",
                f"index.html ({name})",
                lineterm="",
                n=2,
            )
        )
        if diff:
            failed = True
            print(f"\nindex.html's {name} has drifted from the generator:\n")
            print("\n".join(diff))
        else:
            print(f"{name}: in step with the generator")

    if failed:
        print(
            "\nUpdate index.html to match, or change FULL_HEADER / PAGE in "
            "tools/gen-legal.py and regenerate."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
