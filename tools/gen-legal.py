#!/usr/bin/env python3
"""Emit the five legal pages as plain HTML into site/policies/.

The site has no build step, so this generator lives outside the repo and only
its output is committed. Shared chrome lives here so the five pages cannot
drift apart.

Markup in the CONTENT blocks, one directive per line:
    H2: text            section heading
    H3: text            subsection heading
    P: text             paragraph
    C: 3.1|Run-in.|text clause; middle field may be empty for no run-in head
    LI: text            list item (consecutive lines form one list)
    CAPS: text          conspicuous all-caps block, kept as caps on purpose
    NOTE: text          quieter aside

Inline: [label](href) and **bold**.
"""


import argparse
import html
import json
import pathlib
import posixpath
import re

SITE = pathlib.Path(__file__).resolve().parent.parent
# The domain this site will serve from once hoshii.ai points here. Overridable,
# because the same build has to go up on a staging domain first and canonicals
# that point at the wrong host are worse than no canonicals at all. Set by
# --origin; --staging additionally noindexes every page, which is the whole
# point of a staging host: if Google indexes it, you are competing with
# yourself and it may pick the staging domain as canonical.
ORIGIN = "https://www.hoshii.ai/"
STAGING = False

# Per-page sitemap metadata, carried over verbatim from the hand-written
# sitemap.xml this now replaces. Bump a lastmod when that page's content
# actually changes -- Google ignores lastmod entirely if it finds it unreliable,
# so a date that moves on every build is worth less than no date.
SITEMAP = {
    ".": ("2026-08-26", "weekly", "1.0"),
    "demo": ("2026-08-26", "monthly", "0.9"),
    "faq": ("2026-08-26", "monthly", "0.8"),
    "resources": ("2026-08-26", "weekly", "0.8"),
    "customers": ("2026-08-26", "monthly", "0.9"),
    "pricing": ("2026-08-26", "monthly", "0.9"),
    "stutzer-service": ("2026-08-26", "yearly", "0.7"),
    "egger-gemuesebau": ("2026-08-26", "yearly", "0.7"),
    "max-schwarz": ("2026-08-26", "yearly", "0.7"),
    "partners": ("2026-08-26", "monthly", "0.7"),
    "careers": ("2026-08-26", "weekly", "0.6"),
    "imprint": ("2026-08-26", "yearly", "0.3"),
    "privacy-policy": ("2026-08-26", "yearly", "0.3"),
    "cookies-policy": ("2026-08-26", "yearly", "0.3"),
    "about": ("2026-08-27", "monthly", "0.7"),
}

CSS_V = "571"

# Paths are relative, never root-relative: Pages serves this repo from
# /hoshii-site/, so a leading slash would resolve above the site root. Each page
# therefore carries how far up its own root is.

# The h1 can be a full sentence; the browser tab and the search result cannot.
HEAD_TITLES = {
    "about": "About",
    "partners": "Become a partner",
    "careers": "Careers",
    # The page heading is a claim; the browser tab and the search result are not.
    "customers": "Customer stories",
    "pricing": "Pricing",
}

DOCS = [
    ("policies", "privacy-policy", "Privacy Policy"),
    ("policies", "cookies-policy", "Cookies Policy"),
    ("policies", "imprint", "Imprint"),
    ("policies", "msa", "Master Subscription Agreement"),
    ("policies", "sls", "Service Level Specifications"),
    (".", "faq", "Questions"),
    (".", "demo", "Book a demo"),
    (".", "partners", "Bring AI&#8209;driven order processing to your customers, powered by you."),
    (".", "about", "Built in Z&uuml;rich."),
    (".", "careers", "Come build the inbox B2B operations runs on."),
    (".", "resources", "Resources"),
    (".", "customers", "Hoshii is clearing the inboxes<span class=\"doc__line\">of <span class=\"doc__accent\">Europe\u2019s busiest order desks.</span></span>"),
    (".", "pricing", "Pricing"),
    ("customers", "stutzer-service", "High-volume, multilingual order processing on Microsoft Dynamics"),
    ("customers", "egger-gemuesebau", "Voicemail and PDF orders, straight into the CSB ERP"),
    # marinello and adank-davos deliberately have no page: their Framer Content
    # field is empty, so a page could only repeat the headline and the excerpt.
    # Both play on the customers index instead.
    ("customers", "max-schwarz", "Overnight Swiss-German voicemails, ERP-ready before the workday starts"),
]


def inline(t):
    # The content carries deliberate HTML entities, so it is not escaped here.
    # Guard instead: any bare angle bracket would be an authoring mistake.
    if "<" in t or ">" in t:
        raise SystemExit(f"bare angle bracket in content: {t[:60]}")
    for amp in re.findall(r"&\S*", t):
        if not re.match(r"&(?:[a-zA-Z]+|#\d+);", amp):
            raise SystemExit(f"loose ampersand in content: {t[:60]}")
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    return t


# Intrinsic sizes of the client marks, so their boxes can be reserved.
# Card images, with a default for entries that have none of their own.
POST_DIMS = {'post-cost': (540, 960), 'post-agent': (960, 720), 'post-inbox': (540, 960), 'default': (960, 540)}

BELT_MARKS = {
    "casadelvino": ("Casa del Vino", "paper", "2.5rem"),
    "staempfli": ("St\u00e4mpfli", "paper", "2.375rem"),
    "chiefs": ("Chiefs", "paper", "4rem"),
    "stutzer": ("Stutzer", "alpha", "3.25rem"),
    "igp": ("IGP Powder Coatings", "paper", "2rem"),
    "schuetzengarten": ("Sch\u00fctzengarten", "solid", "3.875rem"),
    "egger": ("Egger Gem\u00fcsebau", "paper", "2.75rem"),
    "safruits": ("Safruits", "paper", "2.75rem"),
}

CLIENT_DIMS = {'egger': (299, 300), 'staempfli': (300, 134), 'stutzer': (400, 245), 'schuetzengarten': (300, 165), 'casadelvino': (300, 109), 'chiefs': (480, 300), 'safruits': (300, 300), 'igp': (300, 114)}


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"&\S+?;", "", t).lower()).strip("-")


def render(block, fold=False, up="."):
    """Render a content block. With fold=True each H3 and the paragraphs under
    it become a details/summary pair, which is what the FAQ wants and what a
    contract very much does not."""
    out, pending = [], []
    open_fold = [False]

    def close_fold():
        if open_fold[0]:
            out.append("        </details>")
            open_fold[0] = False

    def flush():
        if pending:
            out.append("        <ul>")
            out.extend(f"          <li>{li}</li>" for li in pending)
            out.append("        </ul>")
            pending.clear()

    for raw in block.strip().split("\n"):
        line = raw.strip()
        if not line:
            continue
        kind, _, rest = line.partition(": ")
        # A directive with no argument ("PROPS:") does not split on ": ".
        if not rest and kind.endswith(":"):
            kind = kind[:-1]
        if kind != "LI":
            flush()
        if fold and kind in ("H2", "H3", "INDEX"):
            close_fold()
        if kind == "H2":
            out.append(f'        <h2 id="{slug(rest)}">{inline(rest)}</h2>')
        elif kind == "INDEX":
            out.append('        <nav class="doc__index" aria-label="Sections">')
            for label in [x.strip() for x in rest.split("|")]:
                out.append(f'          <a href="#{slug(label)}">{label}</a>')
            out.append("        </nav>")
        elif kind == "H3":
            if fold:
                out.append('        <details class="doc__fold">')
                out.append('          <summary class="doc__sum">')
                out.append(f"            <h3>{inline(rest)}</h3>")
                out.append("          </summary>")
                open_fold[0] = True
            else:
                out.append(f"        <h3>{inline(rest)}</h3>")
        elif kind == "P":
            pad = "  " if fold and open_fold[0] else ""
            out.append(f"        {pad}<p>{inline(rest)}</p>")
        elif kind == "LI":
            pending.append(inline(rest))
        elif kind == "CAPS":
            out.append(f'        <p class="doc__caps">{inline(rest)}</p>')
        elif kind == "VALUES":
            out.append('        <ul class="doc__values">')
        elif kind == "ENDVALUES":
            out.append("        </ul>")
        elif kind == "VALUE":
            label, head, body = rest.split("|", 2)
            out.append("          <li>")
            out.append(f'            <p class="doc__valueLabel">{inline(label)}</p>')
            out.append(f'            <h3 class="doc__valueHead">{inline(head)}</h3>')
            out.append(f"            <p>{inline(body)}</p>")
            out.append("          </li>")
        elif kind == "TEAM":
            out.append('        <ul class="doc__team">')
        elif kind == "ENDTEAM":
            out.append("        </ul>")
        elif kind == "PERSON":
            # Not `slug`: that would shadow the slug() helper used for headings.
            name, role, quote, photo = rest.split("|", 3)
            out.append('          <li class="doc__person">')
            if photo:
                out.append('            <picture>')
                out.append(f'              <source srcset="{up}/assets/team/{photo}.avif" type="image/avif" />')
                out.append(f'              <img class="doc__portrait" src="{up}/assets/team/{photo}.jpg" alt="{inline(name)}" width="580" height="720" loading="lazy" />')
                out.append("            </picture>")
            else:
                initials = "".join(w[0] for w in name.split()[:2])
                out.append(f'            <p class="doc__portrait doc__portrait--none" aria-hidden="true">{initials}</p>')
            out.append(f'            <p class="doc__personName">{inline(name)}</p>')
            out.append(f'            <p class="doc__personRole">{inline(role)}</p>')
            if quote:
                out.append(f'            <blockquote class="doc__personQuote">{inline(quote)}</blockquote>')
            out.append("          </li>")
        elif kind == "PLANS":
            out.append('        <ul class="plans">')
        elif kind == "ENDPLANS":
            out.append("        </ul>")
        elif kind == "TOGGLE":
            out.append('        <div class="btoggle" role="group" aria-label="Billing period">')
            out.append('          <button class="btoggle__opt" type="button" data-term="year" aria-pressed="true">Billed annually</button>')
            out.append('          <button class="btoggle__opt" type="button" data-term="month" aria-pressed="false">Billed monthly</button>')
            out.append('        </div>')
        elif kind == "PLAN":
            name, tag, pitch, price, monthly, annual, bullets = rest.split("|", 6)
            rec = " plan--rec" if tag else ""
            out.append(f'          <li class="plan{rec}">')
            if tag:
                out.append(f'            <p class="plan__tag">{inline(tag)}</p>')
            else:
                # Same box, nothing painted: the headline below it starts on the
                # same line as the badged card's does.
                out.append('            <p class="plan__tag plan__tag--none" aria-hidden="true">&nbsp;</p>')
            out.append(f'            <p class="plan__name">{inline(name)}</p>')
            out.append(f'            <p class="plan__pitch">{inline(pitch)}</p>')
            out.append('            <p class="plan__price">')
            out.append(f'              <span class="plan__amt" data-year="{price}" data-month="{monthly}"><span class="plan__cur">&euro;</span>{price}</span>')
            out.append('              <span class="plan__per">per month</span>')
            out.append("            </p>")
            out.append(f'            <p class="plan__terms"><span data-term-note="year">{inline(annual)} billed once a year</span><span data-term-note="month" hidden>billed every month</span></p>')
            out.append('            <ul class="plan__list">')
            for b in [x.strip() for x in bullets.split("~")]:
                out.append(f"              <li>{inline(b)}</li>")
            out.append("            </ul>")
            out.append('            <p class="plan__cta"><a class="btn-os btn-os--accent btn-os--fill" href="{up}/demo.html">Book a demo<span class="btn-os__go" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M3.2 8h9M8.6 4.4 12.2 8l-3.6 3.6"/></svg></span></a></p>'.replace('{up}', up))
            out.append("          </li>")
        elif kind == "TABLE":
            out.append('        <div class="ptable__wrap">')
            out.append('          <table class="ptable">')
            head = [x.strip() for x in rest.split("|")]
            out.append("            <thead><tr>")
            out.append(f'              <th scope="col">{inline(head[0])}</th>')
            for h in head[1:]:
                out.append(f'              <th scope="col">{inline(h)}</th>')
            out.append("            </tr></thead>")
            out.append("            <tbody>")
        elif kind == "ENDTABLE":
            out.append("            </tbody>")
            out.append("          </table>")
            out.append("        </div>")
        elif kind == "GROUP":
            out.append(f'              <tr class="ptable__group"><th scope="rowgroup" colspan="4">{inline(rest)}</th></tr>')
        elif kind == "ROW":
            cells_ = [x.strip() for x in rest.split("|")]
            out.append("              <tr>")
            out.append(f'                <th scope="row">{inline(cells_[0])}</th>')
            for c in cells_[1:]:
                cls = ""
                if c == "Yes":
                    c, cls = "&check;", ' class="is-yes"'
                elif c == "No":
                    c, cls = "&ndash;", ' class="is-no"'
                out.append(f"                <td{cls}>{inline(c)}</td>")
            out.append("              </tr>")
        elif kind == "LIFT":
            # A sentence lifted out of the article itself, set large. Deliberately
            # unattributed: putting words in a named person's mouth to fill a
            # quote slot is not a design decision anyone gets to make.
            out.append('            <blockquote class="lift">')
            out.append(f'              <p class="lift__text">{inline(rest)}</p>')
            out.append("            </blockquote>")
        elif kind == "SHOT":
            src, label = rest.split("|", 1)
            out.append('        <figure class="doc__shot">')
            out.append(
                f'          <img src="{up}/assets/customers/{src}" alt="{inline(label)}" '
                'width="1230" height="779" />'
            )
            out.append("        </figure>")
        elif kind == "VIDEO":
            provider, vid, label = rest.split("|", 2)
            src = (
                f"https://fast.wistia.net/embed/iframe/{vid}?videoFoam=true"
                if provider == "wistia"
                else f"https://player.vimeo.com/video/{vid}?dnt=1"
            )
            out.append('        <div class="doc__video">')
            out.append(
                f'          <iframe src="{src}" title="{inline(label)}" '
                'loading="lazy" allow="autoplay; fullscreen; picture-in-picture" '
                'allowfullscreen></iframe>'
            )
            out.append("        </div>")
        elif kind == "FEATS":
            out.append('        <ul class="feat__list">')
        elif kind == "ENDFEATS":
            out.append("        </ul>")
        elif kind == "FEAT":
            # `logo` is still parsed so the content lines do not have to change,
            # but nothing is drawn with it.
            key, logo, co, tag, year, head, exc, erp, href = rest.split("|", 8)
            out.append('          <li class="feat__item">')
            out.append(f'            <a class="feat__card" href="{up}/{href}">')
            out.append('              <span class="feat__shotwrap">')
            out.append(
                f'                <img class="feat__shot" src="{up}/assets/customers/cover-{key}.jpg" '
                f'alt="" width="1230" height="779" loading="lazy" />'
            )
            out.append("              </span>")
            out.append('              <span class="feat__meta">')
            out.append(f'                <span class="feat__tag">{inline(tag)}</span>')
            out.append(f'                <span class="feat__year">{inline(year)}</span>')
            out.append("              </span>")
            out.append(f'              <span class="feat__head">{inline(head)}</span>')
            out.append(f'              <span class="feat__blurb">{inline(exc)}</span>')
            out.append('              <span class="feat__foot">')
            out.append(f'                <span class="feat__erp">{inline(erp)}</span>')
            out.append('                <span class="feat__go">Read case study'
                       '<span aria-hidden="true">&#8594;</span></span>')
            out.append("              </span>")
            out.append("            </a>")
            out.append("          </li>")
        elif kind == "PAIR":
            out.append('        <div class="pair">')
        elif kind == "ENDPAIR":
            out.append("        </div>")
        elif kind == "STATS":
            out.append('        <ul class="figs">')
        elif kind == "ENDSTATS":
            out.append("        </ul>")
        elif kind == "STAT":
            fig, label = rest.split("|", 1)
            out.append('          <li class="figs__item">')
            out.append(
                f'            <span class="figs__n" data-count="{inline(fig)}">'
                f'{inline(fig)}</span>'
            )
            out.append(f'            <span class="figs__l">{inline(label)}</span>')
            out.append("          </li>")
        elif kind == "CLOSER":
            head, label, href = rest.split("|", 2)
            out.append('        <aside class="docend">')
            out.append(f'          <p class="docend__head">{inline(head)}</p>')
            out.append(
                f'          <a class="btn-os btn-os--fill btn-os--lg" href="{href}">{inline(label)}'
                '<span class="btn-os__go" aria-hidden="true">'
                '<svg viewBox="0 0 16 16"><path d="M3.2 8h9M8.6 4.4 12.2 8l-3.6 3.6"/></svg>'
                "</span></a>"
            )
            out.append("        </aside>")
        elif kind == "CAMS":
            out.append('        <ul class="cam__list">')
        elif kind == "ENDCAMS":
            out.append("        </ul>")
        elif kind == "CAM":
            provider, vid, co, person, role, head, href = rest.split("|", 6)
            src = (
                f"https://fast.wistia.net/embed/iframe/{vid}?videoFoam=true"
                if provider == "wistia"
                else f"https://player.vimeo.com/video/{vid}?dnt=1"
            )
            who = f"{person}, {role}" if person and role else person
            out.append('          <li class="cam__item">')
            out.append('            <div class="cam__frame">')
            out.append(
                f'              <iframe src="{src}" title="{inline(co)} on running Hoshii" '
                'loading="lazy" allow="autoplay; fullscreen; picture-in-picture" '
                'allowfullscreen></iframe>'
            )
            out.append("            </div>")
            out.append('            <div class="cam__body">')
            out.append(f'              <p class="cam__who">{inline(co)}</p>')
            out.append(f'              <p class="cam__head">{inline(head)}</p>')
            if who:
                out.append(f'              <p class="cam__voice">{inline(who)}</p>')
            if href:
                out.append(
                    f'              <a class="cam__more" href="{up}/{href}">Read the full story'
                    '<span class="cam__go" aria-hidden="true">&#8594;</span></a>'
                )
            out.append("            </div>")
            out.append("          </li>")
        elif kind == "STORIES":
            out.append('        <ul class="story__list">')
        elif kind == "ENDSTORIES":
            out.append("        </ul>")
        elif kind == "STORY":
            co, head, exc, erp, person, role, href = rest.split("|", 6)
            out.append('          <li class="story__item">')
            tag, close = (f'<a class="story__card" href="{up}/{href}">', "</a>") if href else ('<div class="story__card">', "</div>")
            out.append(f"            {tag}")
            out.append(f'              <span class="story__who">{inline(co)}</span>')
            out.append(f'              <span class="story__head">{inline(head)}</span>')
            out.append(f'              <span class="story__blurb">{inline(exc)}</span>')
            # Two separate facts, so two separate rows: the system Hoshii writes
            # into, and the person who said this. Joined by a middot they read as
            # one grey string and neither lands.
            foot = []
            if erp:
                foot.append(f'                <span class="story__erp">{inline(erp)}</span>')
            who = f"{person}, {role}" if person and role else person
            if who:
                foot.append(f'                <span class="story__voice">{inline(who)}</span>')
            if foot:
                out.append('              <span class="story__foot">')
                out.extend(foot)
                out.append('              </span>')
            out.append(f"            {close}")
            out.append("          </li>")
        elif kind == "FILTERS":
            out.append('        <div class="res__filters" role="group" aria-label="Filter resources">')
            for i, label in enumerate([x.strip() for x in rest.split("|")]):
                pressed = "true" if i == 0 else "false"
                key = "all" if i == 0 else slug(label)
                out.append(
                    f'          <button class="res__filter" type="button" '
                    f'data-kind="{key}" aria-pressed="{pressed}">{inline(label)}</button>'
                )
            out.append("        </div>")
        elif kind == "ENTRIES":
            out.append('        <ul class="res__list">')
        elif kind == "ENDENTRIES":
            out.append("        </ul>")
        elif kind == "ENTRY":
            kind_, title_, blurb, meta, shot, href = rest.split("|", 5)
            ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
            shot = shot or "default"
            w, h = POST_DIMS[shot]
            out.append(f'          <li class="res__item" data-kind="{slug(kind_)}">')
            out.append(f'            <a class="res__card" href="{href}"{ext}>')
            out.append(
                f'              <img class="res__shot" src="{up}/assets/posts/{shot}.jpg" '
                f'alt="" width="{w}" height="{h}" loading="lazy" />'
            )
            out.append(f'              <span class="res__kind">{inline(kind_)}</span>')
            out.append(f'              <span class="res__title">{inline(title_)}</span>')
            out.append(f'              <span class="res__blurb">{inline(blurb)}</span>')
            if meta:
                out.append(f'              <span class="res__meta">{inline(meta)}</span>')
            out.append("            </a>")
            out.append("          </li>")
        elif kind == "EMPTY":
            out.append(f'        <p class="res__empty" hidden>{inline(rest)}</p>')
        elif kind == "BELT":
            # Same table LOGOS uses; kept beside it so the two cannot drift.
            label, _, picked = rest.partition("|")
            keys = [k.strip() for k in picked.split(",") if k.strip()]
            if label.strip():
                out.append(f'        <p class="doc__proofLabel">{inline(label.strip())}</p>')
            out.append('        <div class="belt" data-anim>')
            # Two tracks. The second is a copy, hidden from assistive tech so the
            # marks are not announced twice.
            for copy in range(2):
                hidden = ' aria-hidden="true"' if copy else ""
                out.append(f'          <ul class="belt__track"{hidden}>')
                for k in keys:
                    alt, treat, h = BELT_MARKS[k]
                    w, hh = CLIENT_DIMS[k]
                    out.append(
                        f'            <li><img class="doc__mark doc__mark--{treat}" '
                        f'style="--h: {h}" src="{up}/assets/clients/n-{k}.png" '
                        f'alt="{"" if copy else alt}" width="{w}" height="{hh}" '
                        'loading="lazy" /></li>'
                    )
                out.append("          </ul>")
            out.append("        </div>")
        elif kind == "PANELS":
            out.append('        <ul class="doc__panels">')
        elif kind == "ENDPANELS":
            out.append("        </ul>")
        elif kind == "PANEL":
            head, body, shot, bloom = rest.split("|", 3)
            out.append(
                f'          <li class="doc__panel" style="--shot: url(\'{up}/assets/img/{shot}\');'
                f' --bloom: {bloom}">'
            )
            out.append(f'            <h3 class="doc__panelHead">{inline(head)}</h3>')
            out.append(f'            <p class="doc__panelBody">{inline(body)}</p>')
            out.append("          </li>")
        elif kind == "AGENDA":
            out.append('        <ol class="agenda">')
        elif kind == "ENDAGENDA":
            out.append("        </ol>")
        elif kind == "SLOT":
            when, what, note = (rest.split("|", 2) + ["", ""])[:3]
            out.append('          <li class="agenda__row">')
            out.append(f'            <span class="agenda__when">{inline(when)}</span>')
            out.append('            <span class="agenda__what">')
            out.append(f'              <span class="agenda__head">{inline(what)}</span>')
            if note:
                out.append(f'              <span class="agenda__note">{inline(note)}</span>')
            out.append("            </span>")
            out.append("          </li>")
        elif kind == "PULL":
            quote_, name, role, photo = rest.split("|", 3)
            out.append('        <figure class="pull">')
            out.append(f'          <blockquote class="pull__text">{inline(quote_)}</blockquote>')
            out.append('          <figcaption class="pull__by">')
            if photo:
                out.append(
                    f'            <img class="pull__face" src="{up}/assets/img/{photo}" '
                    f'alt="" width="288" height="288" loading="lazy" />'
                )
            out.append('            <span class="pull__who">')
            out.append(f'              <span class="pull__name">{inline(name)}</span>')
            out.append(f'              <span class="pull__role">{inline(role)}</span>')
            out.append("            </span>")
            out.append("          </figcaption>")
            out.append("        </figure>")
        elif kind == "CHECKS":
            out.append('        <ul class="doc__checks">')
        elif kind == "ENDCHECKS":
            out.append("        </ul>")
        elif kind == "CHECK":
            out.append(f"          <li>{inline(rest)}</li>")
        elif kind == "ASIDE":
            out.append("<!--ASIDE-->")
        elif kind == "AFTER":
            out.append("<!--AFTER-->")
        elif kind == "HEAD":
            out.append("<!--HEAD-->")
        elif kind == "JOBS":
            out.append('        <ul class="doc__jobs">')
        elif kind == "ENDJOBS":
            out.append("        </ul>")
        elif kind == "JOB":
            # Not an embed: join.com sends frame-ancestors 'none', so its widget
            # URLs cannot be framed at all. These are links out instead.
            title, where, url = rest.split("|", 2)
            out.append("          <li>")
            out.append(
                f'            <a class="doc__job" href="{url}" target="_blank" rel="noopener">'
                f'<span class="doc__jobTitle">{inline(title)}</span>'
                f'<span class="doc__jobWhere">{inline(where)}</span>'
                '<span class="doc__jobGo" aria-hidden="true">&rarr;</span></a>'
            )
            out.append("          </li>")
        elif kind == "PROPS":
            out.append('        <ul class="doc__props">')
        elif kind == "ENDPROPS":
            out.append("        </ul>")
        elif kind == "PROP":
            claim, why = rest.split("|", 1)
            out.append("          <li>")
            out.append(f'            <p class="doc__prop">{inline(claim)}</p>')
            out.append(f'            <p class="doc__propWhy">{inline(why)}</p>')
            out.append("          </li>")
        elif kind == "RAW":
            out.append(rest)
        elif kind == "CTA":
            label, href = rest.split("|", 1)
            out.append(
                f'        <p class="doc__cta"><a class="btn-os btn-os--accent btn-os--fill btn-os--lg" href="{href}">'
                f'{inline(label)}<span class="btn-os__go" aria-hidden="true">'
                '<svg viewBox="0 0 16 16"><path d="M3.2 8h9M8.6 4.4 12.2 8l-3.6 3.6"/></svg>'
                "</span></a></p>"
            )
        elif kind == "NOTE":
            out.append(f'        <p class="doc__note">{inline(rest)}</p>')
        elif kind == "C":
            num, head, body = (rest.split("|", 2) + ["", ""])[:3]
            h = f"<strong>{inline(head)}</strong> " if head else ""
            out.append(
                f'        <p><span class="doc__n">{num}</span> {h}{inline(body)}</p>'
            )
        else:
            raise SystemExit(f"unknown directive: {line[:60]}")
    flush()
    if fold:
        close_fold()
    return "\n".join(out)



SKIP_SCHEMES = ("http://", "https://", "//", "mailto:", "tel:", "data:", "#")


def clean_url(val, link_base):
    """One link, rewritten to a root-relative extensionless URL.

    `link_base` is the directory the page's links were authored against, which
    is the folder the page used to live in, not the directory it is written to
    now. Templates address `{up}/assets/...` and content addresses `demo.html`
    or `../demo.html`, all of it relative to that original folder. Resolving
    against the new nested directory instead sent pricing's CLOSER to
    /pricing/demo/ and the policy cross-links to /msa/.

    Root-relative rather than relative because extensionless URLs make relative
    links fragile: /policies/imprint and /policies/imprint/ have different base
    directories, so the same `../privacy-policy/` resolves to two places
    depending on whether the visitor's URL carried a trailing slash. An absolute
    path cannot be read two ways. The site is served from a domain root, so
    there is no subpath for a leading slash to escape.
    """
    if not val or val.startswith(SKIP_SCHEMES):
        return val
    path, tail = re.match(r"^([^?#]*)(.*)$", val).groups()
    if not path:
        return val
    if path.startswith("/"):
        target = path.lstrip("/")
    else:
        base = "" if link_base in (".", "") else link_base
        target = posixpath.normpath(posixpath.join(base, path))
        if target == ".":
            target = ""
    if target.endswith(".html"):
        stem = target[: -len(".html")]
        # foo/index.html and index.html both address their directory.
        if stem == "index":
            stem = ""
        elif stem.endswith("/index"):
            stem = stem[: -len("/index")]
        return "/" + (stem + "/" if stem else "") + tail
    return "/" + target + tail


def clean_urls(page, link_base):
    return re.sub(
        r'\b(href|src)="([^"]*)"',
        lambda m: f'{m.group(1)}="{clean_url(m.group(2), link_base)}"',
        page,
    )


def page_dir_for(folder, slug):
    """Where a page's directory lives, so its URL needs no extension."""
    return slug if folder == "." else f"{folder}/{slug}"


def url_path_for(folder, slug):
    return page_dir_for(folder, slug) + "/"


MINIMAL_HEADER = """    <header class="titlebar">
      <div class="titlebar__inner">
        <a class="brand" href="{up}/index.html" aria-label="Hoshii home">
          <svg
            class="brand__mark"
            viewBox="0 0 2596 2596"
            width="2596"
            height="2596"
            aria-hidden="true"
          >
            <rect width="2596" height="2596" fill="var(--bone)" />
            <g fill="var(--green)">
              <rect x="673" y="428" width="1259" height="413" />
              <rect x="857" y="1033" width="403" height="1151" />
              <rect x="1380" y="1033" width="402" height="1151" />
            </g>
          </svg>
          <img
            class="brand__wordmark"
            src="{up}/assets/logo/wordmark-a.png"
            alt="Hoshii"
            width="1420"
            height="425"
          />
        </a>

        <div class="titlebar__actions">
          <a class="btn-os btn-os--accent" href="{up}/index.html">Back to site<span class="btn-os__go" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M3.2 8h9M8.6 4.4 12.2 8l-3.6 3.6"/></svg></span></a>
        </div>
      </div>
    </header>
"""

FULL_HEADER = """    <header class="titlebar">
      <div class="titlebar__inner">
        <a class="brand" href="{up}/index.html" aria-label="Hoshii home">
          <svg
            class="brand__mark"
            viewBox="0 0 2596 2596"
            width="2596"
            height="2596"
            aria-hidden="true"
          >
            <rect width="2596" height="2596" fill="var(--bone)" />
            <g fill="var(--green)">
              <rect x="673" y="428" width="1259" height="413" />
              <rect x="857" y="1033" width="403" height="1151" />
              <rect x="1380" y="1033" width="402" height="1151" />
            </g>
          </svg>
          <img
            class="brand__wordmark"
            src="{up}/assets/logo/wordmark-a.png"
            alt="Hoshii"
            width="1420"
            height="425"
          />
        </a>

        <nav class="nav" aria-label="Primary">
          <a class="nav__btn" href="{up}/index.html#product">Product</a>
          <a class="nav__btn" href="{dm}customers.html">Customer stories</a>
          <a class="nav__btn" href="{dm}pricing.html">Pricing</a>
        </nav>

        <div class="titlebar__actions">
          <a class="btn-os btn-os--accent" href="{dm}demo.html">{cta}<span class="btn-os__go" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M3.2 8h9M8.6 4.4 12.2 8l-3.6 3.6"/></svg></span></a>

          <button
            class="menu-toggle"
            type="button"
            aria-expanded="false"
            aria-controls="mobile-nav"
            aria-label="Menu"
          >
            <span class="menu-toggle__bar"></span>
            <span class="menu-toggle__bar"></span>
          </button>
        </div>
      </div>

      <nav class="mobile-nav" id="mobile-nav" aria-label="Primary" hidden>
        <a class="mobile-nav__link" href="{up}/index.html#product">Product</a>
        <a class="mobile-nav__link" href="{dm}customers.html">Customer stories</a>
        <a class="mobile-nav__link" href="{dm}pricing.html">Pricing</a>
      </nav>
    </header>
"""

TOGGLE_JS = """
    <script>
      // Billing toggle. Both prices are already in the markup as data
      // attributes, so switching is a text swap with nothing to fetch.
      (function () {{
        const opts = document.querySelectorAll('.btoggle__opt');
        if (!opts.length) return;
        opts.forEach((btn) => {{
          btn.addEventListener('click', () => {{
            const term = btn.dataset.term;
            opts.forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
            document.querySelectorAll('.plan__amt').forEach((el) => {{
              const cur = el.querySelector('.plan__cur').outerHTML;
              el.innerHTML = cur + el.dataset[term];
            }});
            document.querySelectorAll('[data-term-note]').forEach((el) => {{
              el.hidden = el.dataset.termNote !== term;
            }});
          }});
        }});
      }})();
    </script>
"""

FILTER_JS = """
    <script>
      // Filtering the resource list. Plain attribute toggling, no library: the
      // cards are all in the DOM either way, which keeps them indexable.
      (function () {{
        const filters = document.querySelectorAll('.res__filter');
        const items = document.querySelectorAll('.res__item');
        const empty = document.querySelector('.res__empty');
        if (!filters.length) return;
        filters.forEach((btn) => {{
          btn.addEventListener('click', () => {{
            const kind = btn.dataset.kind;
            filters.forEach((b) =>
              b.setAttribute('aria-pressed', String(b === btn))
            );
            let shown = 0;
            items.forEach((li) => {{
              const match = kind === 'all' || li.dataset.kind === kind;
              li.hidden = !match;
              if (match) shown++;
            }});
            if (empty) empty.hidden = shown > 0;
          }});
        }});
      }})();
    </script>
"""

COUNT_JS = """
    <script>
      // The figures count up once, the first time they are on screen. The final
      // value is already in the markup and is only ever replaced by a number on
      // the way to it, so no-JS and reduced-motion readers see the real figure
      // and nothing here can leave a wrong one behind.
      (function () {
        const figs = document.querySelectorAll('.figs__n[data-count]');
        if (!figs.length) return;
        if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

        const run = (el) => {
          const raw = el.dataset.count;
          // Split the number off any prefix or suffix -- "100+" counts to 100
          // and keeps its plus, "CHF 20" keeps its currency.
          const m = raw.match(/^(\D*)([\d.,]+)(\D*)$/);
          if (!m) return;
          const [, pre, digits, post] = m;
          const target = parseFloat(digits.replace(/,/g, ''));
          if (!isFinite(target)) return;
          const grouped = digits.includes(',');
          const dur = 1100;
          let t0 = null;
          const step = (t) => {
            if (t0 === null) t0 = t;
            const k = Math.min(1, (t - t0) / dur);
            // Ease out, so it decelerates onto the value instead of stopping
            // dead on it.
            const v = Math.round(target * (1 - Math.pow(1 - k, 3)));
            el.textContent = pre + (grouped ? v.toLocaleString('en-US') : v) + post;
            if (k < 1) requestAnimationFrame(step);
            else el.textContent = raw;
          };
          requestAnimationFrame(step);
        };

        const io = new IntersectionObserver(
          (entries) => {
            entries.forEach((e) => {
              if (!e.isIntersecting) return;
              io.unobserve(e.target);
              run(e.target);
            });
          },
          { threshold: 0.6 }
        );
        figs.forEach((el) => io.observe(el));
      })();
    </script>
"""


PATTERN_JS = """

    <script>
      // The pattern layers. The CSS paints a repeating SVG into each one; all this
      // has to do is put the boxes in place, since a background needs an element
      // and these bands do not otherwise have one to spare.
      (function () {
        // Surfaces whose pattern is visible enough to be worth touching.
        const REACT = new Set(['.doc__head', '.askrow', '.closer', '.docend']);

        const HOSTS = [
          ['.doc__head', ['pat']],
          ['.askrow', ['pat--l', 'pat--r']],
          ['.closer', ['pat']],
          ['.pitch__panel', ['pat']],
          ['.cap__art', ['pat']],
          ['.shift__art--flow', ['pat']],
          ['.docend', ['pat']],
        ];
        HOSTS.forEach(([sel, classes]) => {
          document.querySelectorAll(sel).forEach((host) => {
            classes.forEach((cls) => {
              if (host.querySelector(':scope > .' + cls)) return;
              const layer = document.createElement('div');
              layer.className = cls === 'pat' ? 'pat' : 'pat ' + cls;
              // Reactive only where the pattern reads: the page headers, the ask
              // row and the two closing bands.
              if (REACT.has(sel)) layer.classList.add('pat--react');
              layer.setAttribute('aria-hidden', 'true');
              host.appendChild(layer);
            });
          });
        });
      })();
    </script>
    <script>
      // The pattern as real elements, so a tile can react on its own. A painted
      // background has nothing for the browser to hit-test and nothing it can
      // transform.
      //
      // Tiled, not stretched. One tile scaled to cover a layer made the module as
      // wide as the layer over six, which on the wide bands came out enormous; so
      // each layer is a grid of tiles at the module size its surface asks for, and
      // the CSS lays them out.
      //
      // The gradient definitions go in once, into a hidden SVG, and every tile
      // references them by id -- fill="url(#hp-d0)" resolves document-wide, so
      // dozens of tiles share one set of eighteen.
      (function () {
        if (!matchMedia('(hover: hover)').matches) return;
        // Only the surfaces where the pattern is actually visible and at cursor
        // level. Tiling every layer came to 6,000 shapes and a 7,000-element
        // document -- and most of that was the interior art panels, which mask the
        // pattern to one corner at 0.12 opacity. Nobody hover-tilts a shape they
        // cannot see, so those stay painted backgrounds.
        const layers = document.querySelectorAll('.pat--react');
        if (!layers.length) return;

        fetch('/assets/pattern.svg')
          .then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
          .then((text) => {
            const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
            const root = doc.documentElement;
            const defs = root.querySelector('defs');

            if (defs) {
              const holder = document.createElementNS(
                'http://www.w3.org/2000/svg',
                'svg'
              );
              holder.setAttribute('aria-hidden', 'true');
              holder.setAttribute('width', '0');
              holder.setAttribute('height', '0');
              holder.style.position = 'absolute';
              holder.appendChild(defs.cloneNode(true));
              document.body.appendChild(holder);
              defs.remove();
            }

            root.removeAttribute('width');
            root.removeAttribute('height');
            root.setAttribute('preserveAspectRatio', 'none');
            root.setAttribute('aria-hidden', 'true');
            const tile = root.outerHTML;

            layers.forEach((layer) => {
              const mod =
                parseFloat(getComputedStyle(layer).getPropertyValue('--pat-mod')) || 48;
              const r = layer.getBoundingClientRect();
              if (!r.width || !r.height) return;
              // Exactly enough tiles to cover, and the column count is handed to
              // the CSS rather than left to auto-fill -- auto-fill only creates
              // tracks that fit, so the tile covering a remainder at the right edge
              // would have wrapped to a new row instead.
              const cols = Math.ceil(r.width / (mod * 6));
              const rows = Math.ceil(r.height / (mod * 4));
              layer.style.setProperty('--pat-cols', String(cols));
              layer.insertAdjacentHTML('afterbegin', tile.repeat(cols * rows));
              layer.classList.add('pat--live');
            });
          })
          .catch(() => {});
      })();
    </script>
    <script>
      // Where the cursor is, the pattern gains a little density. One listener for
      // the whole page rather than one per layer: these bands are large, several
      // of them overlap, and per-layer enter/leave fired in the wrong order where
      // they nested.
      //
      // Only two custom properties are written per layer per frame -- the mask
      // that reveals the doubled copy is entirely CSS, so nothing here touches
      // layout or paints anything itself.
      (function () {
        if (!matchMedia('(hover: hover)').matches) return;
        if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const layers = [...document.querySelectorAll('.pat')];
        if (!layers.length) return;

        let at = null;
        let frame = null;

        const paint = () => {
          frame = null;
          layers.forEach((el) => {
            const r = el.getBoundingClientRect();
            if (!r.width || !r.height) return;
            const inside =
              at &&
              at.x >= r.left - 40 &&
              at.x <= r.right + 40 &&
              at.y >= r.top - 40 &&
              at.y <= r.bottom + 40;
            if (!inside) {
              el.classList.remove('pat--near');
              return;
            }
            // Percentages, so the mask keeps its position if the layer resizes
            // between frames.
            el.style.setProperty('--mx', (((at.x - r.left) / r.width) * 100).toFixed(2) + '%');
            el.style.setProperty('--my', (((at.y - r.top) / r.height) * 100).toFixed(2) + '%');
            el.classList.add('pat--near');
          });
        };

        addEventListener(
          'pointermove',
          (e) => {
            if (e.pointerType === 'touch') return;
            at = { x: e.clientX, y: e.clientY };
            if (frame !== null) return;
            if (document.hidden) paint();
            else frame = requestAnimationFrame(paint);
          },
          { passive: true }
        );

        addEventListener('pointerleave', () => {
          at = null;
          layers.forEach((el) => el.classList.remove('pat--near'));
        });
      })();
    </script>
"""


MENU_JS = """
    <script>
      // The only script these pages need: the mobile menu on the full header.
      const toggle = document.querySelector('.menu-toggle');
      const mobileNav = document.querySelector('.mobile-nav');
      if (toggle && mobileNav) {{
        toggle.addEventListener('click', () => {{
          const open = toggle.getAttribute('aria-expanded') === 'true';
          toggle.setAttribute('aria-expanded', String(!open));
          mobileNav.hidden = open;
        }});
      }}
    </script>
"""

# On the booking page the header CTA would otherwise link to the page it is
# already on and repeat its title, so it invites instead.
HEADER_CTA = {"demo": "Let&rsquo;s chat"}

# Marketing pages keep the site nav; the legal documents and the FAQ stay on
# the stripped bar, where a full nav would just be noise around a document.
FULL_NAV = {
    "partners", "careers", "resources", "customers", "pricing", "demo", "about",
    "stutzer-service", "egger-gemuesebau", "max-schwarz",
    # faq is an answer-engine landing page, not a legal document: organic traffic
    # arrives on it cold and needs somewhere to go next.
    "faq",
}

# Contract documents that have to exist at a stable URL -- an order form links
# to them -- but that are not part of the site: no footer link, no sitemap entry,
# and a robots meta telling crawlers to leave them out of the index.
NOINDEX = {"msa", "sls"}

# The careers page lays out a values grid and six portraits, which will not fit
# a prose measure. Prose inside it stays capped so the reading column holds.
WIDE = {"careers", "resources", "customers", "pricing", "about"}


CASE_MAIN = """      <div class="doc__head">
        <div class="doc__inner">
          <h1 class="doc__title">{title}</h1>{stand}
        </div>
      </div>

      <div class="doc__band guides">
        <div class="doc__inner case doc__body">
{body}
        </div>
      </div>"""

PLAIN_MAIN = """      <div class="doc__head">
        <div class="doc__inner">
          <h1 class="doc__title">{title}</h1>{stand}
        </div>
      </div>

      <div class="doc__band guides">
        <div class="doc__inner doc__body">
{body}
        </div>
      </div>"""

SPLIT_MAIN = """      <div class="doc__head doc__head--intro">
        <div class="doc__inner">
          <div class="doc__lede">
            <h1 class="doc__title">{title}</h1>{stand}
          </div>
{head}
        </div>
      </div>

      <div class="doc__band guides">
        <div class="doc__inner doc__split">
          <div class="doc__splitMain doc__body">
{body}
          </div>

          <div class="doc__splitAside">
{aside}
          </div>
        </div>
      </div>
{after}"""

# Pages whose whole purpose is the form get it beside the copy, not under it.
SPLIT = {"partners"}

# Case studies run the full band: a reading column with a rail beside it holding
# the numbers the prose states and a quote lifted out of it. A single narrow
# column left two thirds of the band empty.
CASE = {"stutzer-service", "egger-gemuesebau", "max-schwarz"}

# The booking page has its own template: two columns from the top, split by a
# single rule, with the form sticky in the right one. It stopped fitting the
# document scaffolding once the argument moved above the fold.
BOOK = {"demo"}

BOOK_MAIN = """      <div class="book">
        <div class="book__grid">
          <div class="book__pitch">
            <h1 class="book__title">{title}</h1>
            <p class="book__deck">{stand}</p>
{body}
          </div>

          <div class="book__form">
{aside}
          </div>
        </div>
      </div>
{after}"""

PAGE = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{head_title} | Hoshii</title>
    <meta name="description" content="{desc}" />
{robots}    <link rel="canonical" href="{site}{path}" />
    <link rel="icon" href="{up}/favicon.svg" type="image/svg+xml" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Hoshii" />
    <meta property="og:title" content="{head_title} | Hoshii" />
    <meta property="og:description" content="{desc}" />
    <meta property="og:url" content="{site}{path}" />
    <meta property="og:image" content="{site}assets/img/hero-slot.jpg" />
    <meta name="twitter:card" content="summary_large_image" />
    <link rel="stylesheet" href="{up}/styles.css?v={v}" />
{head}  </head>
  <body>
{header}
    <main class="{main_cls}{wide}">
{main}
    </main>

    <footer class="foot">
      <div class="foot__inner">
        <div class="foot__brand">
          <a class="brand brand--foot" href="{up}/index.html" aria-label="Hoshii home">
            <svg class="brand__mark" viewBox="0 0 2596 2596" aria-hidden="true">
              <rect width="2596" height="2596" fill="var(--green)" />
              <g fill="var(--bone)">
                <rect x="673" y="428" width="1259" height="413" />
                <rect x="857" y="1033" width="403" height="1151" />
                <rect x="1380" y="1033" width="402" height="1151" />
              </g>
            </svg>
            <img
              class="brand__wordmark"
              src="{up}/assets/logo/wordmark-b.png"
              alt="Hoshii"
              width="1420"
              height="425"
              loading="lazy"
            />
          </a>
          <p class="foot__line">
            The AI&#8209;native inbox for B2B operations. Built in Zurich for the teams
            that keep goods moving.
          </p>
        </div>

        <nav class="foot__nav" aria-label="Footer">
          <div class="foot__col">
            <h2 class="foot__head">Product</h2>
            <a class="foot__link" href="{up}/index.html#product">Product</a>
            <a class="foot__link" href="{dm}pricing.html">Pricing</a>
            <a class="foot__link" href="{dm}customers.html">Customer stories</a>
          </div>

          <div class="foot__col">
            <h2 class="foot__head">Company</h2>
            <a class="foot__link" href="{dm}resources.html">Resources</a>
            <a class="foot__link" href="{dm}faq.html">Questions</a>
            <a class="foot__link" href="{dm}careers.html">Careers</a>
            <a class="foot__link" href="{dm}partners.html">Become a partner</a>
            <a class="foot__link" href="{dm}about.html">About</a>
            <a class="foot__link" href="{dm}demo.html">Book a demo</a>
          </div>

          <div class="foot__col">
            <h2 class="foot__head">Legal</h2>
            <a class="foot__link" href="{lg}imprint.html">Imprint</a>
            <a class="foot__link" href="{lg}privacy-policy.html">Privacy</a>
            <a class="foot__link" href="{lg}cookies-policy.html">Cookies</a>
          </div>
        </nav>
      </div>

      <p class="foot__base">
        <span>&copy; 2026 Hoshii</span>
        <span>Z&uuml;rich, Switzerland</span>
      </p>
    </footer>
{script}  </body>
</html>
"""

# ---------------------------------------------------------------------------
# Content. Transcribed as supplied. Typography normalised (curly quotes, en and
# em dashes, one space after punctuation) and unambiguous transcription slips
# corrected -- "Order From" to "Order Form", "CONDLUDED" to "CONCLUDED",
# "up-dates" to "updates", "P ayment Date" to "Payment Date", and the stray
# space before several run-in headings removed. Nothing else is edited: the
# duplicate clause numbers, the repeated paragraphs, the missing tables and the
# broken cross-reference in 4.1 are left exactly as they arrived.
# ---------------------------------------------------------------------------

PRIVACY = """
P: hoshii.ai is owned by Hoshii, which is a data controller of your personal data.
P: We have adopted this Privacy Policy, which determines how we are processing the information collected by hoshii.ai, which also provides the reasons why we must collect certain personal data about you. Therefore, you must read this Privacy Policy before using the hoshii.ai website.
P: We take care of your personal data and undertake to guarantee its confidentiality and security.
H2: Personal information we collect
P: When you visit the Site, we automatically collect certain information about your device, including information about your web browser, IP address, time zone, and some of the installed cookies on your device. As you browse the Site, we collect information about the individual pages you view, what referred you to the Site, and how you interact with it. We refer to this as &ldquo;Device Information.&rdquo; We might also collect the personal data you provide to us (name, address, payment information, etc.) to fulfil the agreement.
H2: Why do we process your data?
P: Our top priority is customer data security, and as such we process only minimal user data, only as much as absolutely necessary to maintain the website. Information collected automatically is used only to identify potential cases of abuse and establish statistical information regarding website usage.
P: You can visit the website without telling us who you are. If you wish to use some features, receive our newsletter, or fill in a form, you may provide personal data such as your email and name. Users uncertain about what information is mandatory are welcome to contact us.
H2: Your rights
P: If you are a European resident, you have the following rights related to your personal data:
LI: The right to be informed.
LI: The right of access.
LI: The right to rectification.
LI: The right to erasure.
LI: The right to restrict processing.
LI: The right to data portability.
LI: The right to object.
LI: Rights in relation to automated decision-making and profiling.
H2: Information security
P: We secure the information you provide on computer servers in a controlled, secure environment, protected from unauthorized access, use, or disclosure. However, no data transmission over the Internet or wireless network can be guaranteed.
H2: Contact information
P: If you wish to contact us concerning any matter relating to your individual rights and your Personal Information, send an email to [contact@hoshii.ai](mailto:contact@hoshii.ai).
"""

COOKIES = """
P: This is the Cookie Policy for Hoshii, accessible from hoshii.ai.
H2: What are cookies
P: As is common practice with almost all professional websites this site uses cookies, which are tiny files downloaded to your computer, to improve your experience. This page describes what information they gather, how we use it, and why we sometimes need to store these cookies.
H2: How we use cookies
P: We use cookies for a variety of reasons detailed below. In most cases there are no industry standard options for disabling cookies without completely disabling the functionality they add to this site. It is recommended that you leave on all cookies if you are not sure whether you need them.
H2: Disabling cookies
P: You can prevent the setting of cookies by adjusting the settings on your browser. Be aware that disabling cookies will affect the functionality of this and many other websites that you visit.
H2: The cookies we set
P: **Forms related cookies:** when you submit data through a form, such as those found on contact pages, cookies may be set to remember your user details for future correspondence.
H2: Third party cookies
P: In some special cases we also use cookies provided by trusted third parties. This site uses Google Analytics to help us understand how you use the site and ways we can improve your experience.
H2: More information
P: If you are still looking for more information, you can contact us through one of our preferred contact methods: [contact@hoshii.ai](mailto:contact@hoshii.ai).
"""

IMPRINT = """
H2: Responsible entity
P: Hoshii AG
P: Zollikerstrasse 1, 8008 Z&uuml;rich, Switzerland
P: [contact@hoshii.ai](mailto:contact@hoshii.ai)
H2: Disclaimer
P: The author assumes no liability for the correctness, accuracy, timeliness, reliability, or completeness of the information.
P: Liability claims against the author for damages of a material or immaterial nature arising from access to or use or non-use of the published information are excluded.
P: All offers are non-binding. The author expressly reserves the right to change, supplement, or delete parts of the pages without separate announcement.
H2: Disclaimer for content and links
P: References and links to third-party websites lie outside our area of responsibility. We decline any responsibility for such websites. Access to and use of such websites is at the respective user&rsquo;s own risk.
H2: Copyright declaration
P: The copyright and all other rights to content, images, photos, or other files on this website belong exclusively to Hoshii or the specifically named rights holders. Written consent from the copyright holder must be obtained in advance for the reproduction of any elements.
"""

MSA = """
H2: 1. Scope
C: 1.1||This MSA governs the use of the Hoshii Platform (as defined below) and any services provided in connection with it (&ldquo;Services&rdquo;).
C: 1.2||The Services are accessible to all organizations except direct competitors or as otherwise specified in the Agreement. Competitors are prohibited from accessing the Services unless Hoshii consents to such access in advance.
C: 1.3||Any order by the Customer is subject to review and acceptance by Provider.
C: 1.4||The &ldquo;Agreement&rdquo; between the Customer and Hoshii consists of this MSA and, if applicable, the order form or other personalized offer (&ldquo;Order Form&rdquo;) provided by Provider (collectively, the &ldquo;Agreement&rdquo;). All documents referenced in this MSA, as published on the website on the Effective Date, are incorporated by reference and made part of this Agreement unless explicitly stated otherwise. The &ldquo;Effective Date&rdquo; means the date specified in the Order Form or, in the absence of an Order Form, the date the Customer starts using the Services.
H2: 2. Services
H3: Hoshii Platform
C: 2.1.1||&ldquo;Hoshii Platform&rdquo; or &ldquo;Platform&rdquo; means Hoshii&rsquo;s proprietary Software-as-a-Service (SaaS) platform that automates the entry of data into the Customer&rsquo;s Enterprise Resource Planning (ERP) systems from orders received by the Customer through various channels, including but not limited to email and voicemail. The term encompasses the platform&rsquo;s core functionalities, all features, modules, and add-ons as specified in the applicable Order Form.
C: 2.1.2||If any functionality, module, feature, add-on, or other component of the Platform is provided free of charge, Provider reserves the right, in its sole discretion, to terminate such free component at any time without any obligation to provide a substitute or alternative. The Platform, excluding any components provided free of charge, is provided in accordance with the Service Level Specifications available at [hoshii.ai/sls](sls.html) (&ldquo;SLS&rdquo;).
C: 2.1.3||To ensure the Hoshii Platform remains up to date and effective, Hoshii may modify or discontinue individual components of the Hoshii Platform at any time, provided that such modifications or discontinuations do not materially diminish the overall functionality or availability of the Services for paying Customers during their current subscription term.
H3: Consulting Services
C: 2.2.1||Complementing the Platform, the Provider offers consulting, maintenance, training, and support services (collectively, &ldquo;Consulting Services&rdquo;). The Customer may purchase these Consulting Services for support during setup and onboarding, as well as for ongoing needs.
C: 2.2.1||The specific scope of the Consulting Services to be provided is detailed in the Order Form.
H3: Tailored Solutions
C: 2.3.1||In addition to the above Services, the Provider offers tailored solutions, such as custom APIs, integrations, or other solutions (&ldquo;Tailored Solutions&rdquo;), to meet specific Customer requirements.
C: 2.3.2||The specific scope, specifications, and delivery timelines for the Tailored Solutions shall be as set forth in the applicable Order Form. The Provider shall use commercially reasonable efforts to deliver the Tailored Solutions in accordance with such specifications and timelines, provided that the Customer timely fulfills all of its obligations necessary for the Provider to perform, including but not limited to providing necessary access, information, and approvals.
C: 2.3.3||Upon delivery of any Tailored Solution or portion thereof, the Customer shall have fifteen (15) days (the &ldquo;Test Period&rdquo;) to test such deliverable to confirm it meets the specifications set forth in the Order Form. If the Customer identifies any material non-conformity during the Test Period, the Customer shall provide written notice by email to the Provider detailing the defect. The Provider shall then have two (2) attempts to remedy such defect within a reasonable timeframe. If the Provider fails to remedy the defect after two attempts, the Customer may, at its option: (i) allow additional remedy attempts; (ii) accept the deliverable with a mutually agreed adjustment to the fees; or (iii) terminate the applicable Order Form for such Tailored Solution and receive a partial or full refund of any prepaid fees for undelivered work. If the Customer does not provide written notice of any defect within the Test Period, the deliverable shall be deemed accepted. This section does not apply to Tailored Solutions that are not intended to be tested.
C: 2.3.4||Prior to final delivery and acceptance of a Tailored Solution, the Customer may request modifications to the specifications by submitting a written change request to the Provider. The Provider shall review such request and provide a written response indicating whether the modification is feasible and any impact on timelines, costs, or other terms. No modification shall be binding unless mutually agreed in writing by both parties. The Customer acknowledges that modification requests may result in adjustments to the delivery schedule and fees.
H2: 3. Payment
C: 3.1|General.|The fees of the Services are specified in the Order Form and in the absence of such specification, the Services shall be invoiced at the Provider&rsquo;s standard rates (&ldquo;Standard Rates&rdquo; are defined and as set forth in the SLS). All prices displayed on the Provider&rsquo;s marketing materials are indicative and non-binding and Provider reserves the right to modify, update, or discontinue any prices or offers at any time without prior notice.
C: 3.2|Currency, Taxes.|Unless otherwise stated in the Order Form:
P: (a) all prices are in Swiss Francs (CHF);
P: (b) all prices are subject to any applicable value-added, sales or other taxes, duties or charges imposed on the Services (&ldquo;Taxes&rdquo;). The Customer is responsible for the payment of all Taxes associated with the Services unless the Customer provides the Provider with a valid tax exemption certificate approved by the appropriate tax authorities. If the Provider becomes liable for such Taxes, for whatever reason, the Customer undertakes to immediately reimburse the Provider. The Parties agree, where possible, on a reverse charge procedure to simplify the payment of Taxes;
P: (c) the Customer is responsible for any bank or other fees incurred in the payment of the Services. All amounts are to be paid in full without any set-off, deduction or withholding.
C: 3.3|Expenses.|Any applicable expenses by Provider are specified in the Order Form. Any additional expenses require the Customer&rsquo;s prior approval.
C: 3.4|Payment Date.|All payments are due in full within fifteen (15) days of invoicing, or as otherwise specified in the Order Form. Annual or monthly charges for use of the Services will be invoiced in advance of the relevant period. Upon expiration of the payment term, the Customer will be in default without the need for a reminder or overdue notice. The Provider is entitled to charge interest on overdue payments at a rate of 5% per annum, calculated from the invoice date until full payment, including all accrued interest, is received.
C: 3.5|Allocated Hours.|If a purchase of Services includes a specific number of service hours (&ldquo;Allocated Hours&rdquo;), those hours must be used within the term set forth in the Order Form or other documentation provided by the Provider, which shall be a calendar year from the date of purchase unless otherwise specified. Any unused hours will be forfeited and will not roll over to the following term. If the Allocated Hours are exceeded, the additional hours will be invoiced at the Provider&rsquo;s Standard Rates.
C: 3.6|Estimated Hours.|Furthermore, if an Order Form specifies a set number of service hours for a project, this number is considered an estimate (&ldquo;Estimated Hours&rdquo;) unless otherwise explicitly stated. The actual number of hours required may exceed the Estimated Hours. Any excess hours will be invoiced at the Provider&rsquo;s Standard Rates, except as specified in the Order Form.
H2: 4. Intellectual Property
C: 4.1|Ownership.|Hoshii owns and shall retain sole and exclusive ownership of the Hoshii Platform, any Tailored Solution, and any other deliverable provided under this Agreement (collectively the &ldquo;Platform Technology&rdquo;), including all IP Rights (as defined below) related thereto, as well as any improvements, developments, modifications, or changes made to any of the foregoing during the term of this Agreement, whether by Provider, the Customer, or any third party. &ldquo;Intellectual Property Rights&rdquo; or &ldquo;IP Rights&rdquo; means all worldwide rights, title, and interest in and to any and all intellectual property, including but not limited to patents, utility models, designs, copyrights (including moral rights), trade secrets, confidential information, trademarks, service marks, trade names, domain names, mask work rights, database rights, rights in computer software (including source code and object code), algorithms, inventions, discoveries, improvements, developments, processes, methods, techniques, know-how, and any other intellectual property or proprietary rights of every kind and nature, whether now known or hereafter existing, whether registered or unregistered, capable of registration or not, or protectable under applicable law or not, including any applications for registration, renewals, extensions, and all other related rights, the rights to sue for past, present, and future infringement or misappropriation, and all goodwill associated therewith.
P: Notwithstanding anything to the contrary in the Agreement, including the Order Form, the Customer explicitly acknowledges that no rights, titles, or interests in the Platform Technology or IP Rights related thereto are assigned, transferred, or conveyed under this Agreement. Except as expressly provided in section Fehler! Verweisquelle konnte nicht gefunden werden., no license or other rights are granted to any Platform Technology.
C: 4.2|Licence.|Subject to the terms and conditions of this Agreement, including the payment of all applicable fees, Provider hereby grants to the Customer a non-exclusive, non-transferable, non-sublicensable, limited license to use the Hoshii Platform, any Tailored Solution, and any other deliverables provided under this Agreement, solely for the Customer&rsquo;s internal business purposes during the term of this Agreement, as specified in the applicable Order Form.
P: Any open source or third-party software included in the Platform Technology will be provided in accordance with the open source or third-party license.
C: 4.3|Customer Content.|The Customer is the sole and exclusive owner of its own content, logos, marks, etc. and any related IP Rights, and will retain all rights, title and interest in such content and works. The Customer grants Provider a limited right to use such content and works during the term of this Agreement, if and to the extent necessary to provide the Services to the Customer.
C: 4.4|Customer Obligations.|The Customer shall (i) not distribute, or otherwise make available the Platform Technology to any third party without Provider&rsquo;s prior written consent; (ii) not reverse engineer, disassemble or decompile, or attempt to reverse engineer, disassemble or decompile the Platform Technology; (iii) comply with all applicable laws and regulations in connection with its use of the Platform Technology; (iv) offer the necessary assistance with regard to failure analyses, and promptly report or forward any complaints and claims related to the Services, (v) not modify or alter the Platform Technology (including future versions) in any way (other than through the configuration options provided by Provider) without Provider&rsquo;s prior written consent; (vi) not create derivative works of the Platform Technology; (vii) not copy or otherwise reproduce, in whole or in part, the Technology Platform; (viii) not modify or remove any labels or copyright notices in Provider&rsquo;s Services; (ix) not manipulate Provider&rsquo;s Services and infrastructure; (x) not use the Services for illegal, unfair or offensive purposes; (xi) not distribute viruses, Trojan horses or other malicious software through the Services, (xii) not scrape the Services by means of automated scripts, (xiii) not circumvent or attempt to circumvent any technical limitations or restrictions of Hoshii&rsquo;s Services, and (xiv) not to use the Services in such a way that Hoshii would be subject to regulatory supervision, responsibility or otherwise obliged to comply with legal provisions.
H2: 5. Warranty
P: The Services are provided are provided on an &ldquo;AS IS&rdquo; basis, and the Provider and its affiliates make no warranties, and any and all warranties are excluded, whether express, implied, statutory, or otherwise, including but not limited to warranties of merchantability, quality, or fitness for a particular purpose, unless otherwise explicitly stated in the Order Form.
P: In particular, the Provider disclaims any representation or warranty, that the Platform will be uninterrupted or error-free, or meets the Customer&rsquo;s specific requirements.
H2: 6. Limitation of Liability
C: 6.1|General.|Unless a specific section explicitly provides for a full exclusion of liability to the maximum extent permitted by law, the limitations and exclusions of liability set forth in this section 6 shall apply to all sections of this Agreement.
C: 6.2|Limitation.|
CAPS: PROVIDER&rsquo;S AND CUSTOMER&rsquo;S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT, WHETHER IN CONTRACT, TORT, BREACH OF STATUTORY DUTY OR OTHERWISE, SHALL NOT EXCEED THE SERVICES PURCHASED THAT GAVE RISE TO THE RELEVANT CLAIM, PROVIDED THAT IF THE AGREEMENT IS CONCLUDED FOR A TERM EXCEEDING 12 MONTHS, THE TOTAL AGGREGATE LIABILITY SHALL BE LIMITED TO THE AMOUNT DUE DURING THE LAST 12 MONTHS OF THE AGREEMENT PRIOR TO THE CLAIM. NEITHER PARTY WILL BE LIABLE FOR ANY LOST PROFITS, REVENUE, BUSINESS, VALUE, CUSTOMERS, ANTICIPATED SAVINGS, DATA, REPUTATION, GOODWILL OR INDIRECT, EXEMPLARY, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES SUFFERED BY THE OTHER PARTY, TO THE FULLEST EXTENT PERMITTED BY LAW. NOTWITHSTANDING THE ABOVE, NOTHING IN THIS AGREEMENT WILL EXCLUDE OR LIMIT IN ANY WAY THE LIABILITY FOR (i) ANY INFRINGEMENT OF THE PROVIDER&rsquo;S RIGHTS PERTAINING TO ITS PLATFORM TECHNOLOGY, OR (ii) GROSS NEGLIGENCE, WILLFUL MISCONDUCT, FRAUD, DEATH, PERSONAL INJURY, OR ANY OTHER LIABILITY THAT CANNOT BE EXCLUDED OR LIMITED UNDER APPLICABLE LAW.
C: 6.3|Infringement of Third-Party Rights.|The Provider shall indemnify, defend, and hold harmless the Customer, its affiliates, and their respective officers, directors, employees, and agents (collectively, the &ldquo;Indemnitees&rdquo;) from and against any and all valid claims, liabilities, damages, losses, costs, and expenses (including reasonable attorneys&rsquo; fees and expenses) arising out of or related to any actual negligence, willful misconduct, or breach of this Agreement by the Provider in connection with the Provider&rsquo;s Services that result in the infringement of any third party&rsquo;s intellectual property rights, provided that (i) the Customer immediately notifies the Provider of the claim and the impending assertion of a claim, (ii) the Provider is granted sole authority to investigate, defend or settle the claim, and (iii) the Provider is provided with the requested assistance in investigating, preparing, defending and settling the claim, subject to reimbursement of the Customer&rsquo;s reasonable expenses.
C: 6.4|Exclusion.|The Customer shall fully indemnify, defend, and hold harmless the Provider, its affiliates, and their respective officers, directors, employees, and agents from and against any and all claims, liabilities, damages, losses, costs, expenses (including reasonable attorneys&rsquo; fees and expenses), judgments, and penalties arising out of or related to: (i) the Customer&rsquo;s misuse, improper use, handling, storage, alteration, or unauthorized modification of the Platform Technology; (ii) the Customer&rsquo;s violation of any applicable laws, regulations, or the Customer&rsquo;s failure to obtain necessary licenses, permits, or consents in connection with the export, installation, or use of the Platform Technology; or (iii) any action, proceeding, or claim brought against the Provider for infringement of any existing rights of a third party, including but not limited to intellectual property rights, in connection with the use, misuse, or modification of the Platform Technology by the Customer or any third party acting on the Customer&rsquo;s behalf.
H2: 7. Confidentiality, Data Protection
H3: Confidentiality
C: 7.1.1||The Parties agree to keep the Confidential Information (as defined below) strictly confidential and to take all reasonable precautions to prevent its unauthorized use or disclosure. The Parties agree not to use the Confidential Information for any purpose other than the performance of this Agreement.
P: Without limitation, any non-public information disclosed by one Party to the other and any information in connection with the Platform Technology is considered &ldquo;Confidential Information&rdquo;. Other &ldquo;Confidential Information&rdquo; includes information that is (i) designated as such in writing or in another tangible form by the disclosing Party at the time of disclosure and clearly marked as &ldquo;confidential,&rdquo; &ldquo;proprietary,&rdquo; or similar; (ii) if initially disclosed orally or in another intangible form, designated as &ldquo;confidential,&rdquo; &ldquo;proprietary,&rdquo; or similar at the time of disclosure, and subsequently confirmed in tangible form and provided to the receiving Party by the disclosing Party within 30 days of the initial disclosure; or (iii) otherwise reasonably considered confidential at the time of disclosure.
P: Notwithstanding the foregoing, Confidential Information does not include any information that (i) is now or at a later date generally available to the public through no fault of the Receiving Party; (ii) was demonstrably in the Receiving Party&rsquo;s lawful possession prior to its disclosure by the disclosing Party; (iii) was independently developed by a Party without the use of Confidential Information; or (iv) a Party lawfully receives from a third party that has the right to disclose the Confidential Information.
H3: Data Protection
C: 7.2.1||Each Party shall comply with the data protection laws applicable to the respective Party. The Customer warrants that it is authorized to transfer any personal data to Provider for processing and that such transfer complies with applicable laws.
P: Each Party shall comply with the data protection laws applicable to the respective Party. The Customer warrants that it is authorized to transfer any personal data to Provider for processing and that such transfer complies with applicable laws.
P: Where Provider processes personal data on behalf of the Customer, such processing shall be governed by the Data Processing Agreement (DPA) available at hoshii.ai/dpa.
P: The Customer is responsible for ensuring that the collection and processing of sensitive personal data (as defined under applicable laws, including special categories under GDPR Article 9) through the Services complies with legal requirements. Provider does not currently provide specific technical solutions for the enhanced protection of sensitive personal data. The Customer shall indemnify Provider against any claims, losses, or liabilities arising from the Customer&rsquo;s unauthorized collection or processing of sensitive personal data, provided that Hoshii has complied with its obligations under the DPA and applicable laws.
P: Further information on how Provider processes data is available in our [Privacy Policy](privacy-policy.html).
H2: 8. Term, Termination
C: 8.1||The term of the Agreement is specified in the Order Form. The Agreement will be renewed for successive terms of the same length unless terminated by either party in writing (e.g., by e-mail) at least sixty (60) days prior to the expiration of the term.
C: 8.2||Either Party may terminate this Agreement in writing at any time (i) in the event of a material breach of this Agreement by the other Party not cured within thirty (30) days after written notice of such breach, or (ii) if the Services are used in a manner not in accordance with this Agreement.
C: 8.3||Upon termination any rights of use and other rights granted to the Customer under this Agreement are terminated, and the Customer agrees to immediately pay all outstanding costs, fees and otherwise owed amounts (for the avoidance of doubt, it is stated that in the event of premature termination for which the Customer is responsible, the costs, fees and other amounts owed will be owed for the entire term of the Agreement).
C: 8.4||The rights and obligations of the Parties that by their nature or context are intended to survive the termination or expiration of this Agreement shall survive, including, but not limited to, obligations regarding confidentiality, indemnification, limitation of liability, and any accrued rights or payment obligations.
H2: 9. Miscellaneous
C: 9.1|Marketing.|The Customer agrees that Hoshii may, during the term of the Agreement and after its termination, use the Customer&rsquo;s name and logo as well as respective case studies on its website and in other materials (flyers, brochures, presentations, use cases, newsletters, etc.), and may name the Customer as a customer or user. The Customer may revoke this permission, in whole or in part, at any time by written notice (e.g., by e-mail).
P: In addition, the Customer agrees to receive information about Hoshii&rsquo;s Services and offers (e.g., via e-mail) during and after termination of the Agreement. The instructions for opting out of these mailings can be found in the corresponding messages.
C: 9.2|Entire Agreement.|This Agreement (as defined in Section 1.4) constitutes the entire Agreement between Provider and the Customer with respect to the Services and supersedes any agreement or understanding with respect to the subject matter hereof that may have been concluded prior to the Effective Date. Any additional agreements are null and void, unless expressly incorporated into and referenced within an Order Form issued by Provider and duly executed by both parties in accordance with the terms of this Agreement.
C: 9.3|Severability.|If at any time any provision or part of a provision of this Agreement is or becomes invalid or unenforceable, then neither the validity nor the enforceability of the remaining provisions or the remaining part of the provision will in any way be affected or impaired. In this case, Hoshii undertakes to immediately replace the invalid provision with a valid provision which best reflects the original intention in terms of its content.
C: 9.4|Assignment.|Neither Party may assign its rights or obligations under this Agreement to any third party without the prior written consent of the other Party (which will not be unreasonably withheld); provided, however, that either Party may assign this Agreement in its entirety (including all Order Forms), without the consent of the other Party, to an affiliate or in connection with a merger, acquisition, corporate reorganization or sale of all or substantially all of its assets. Subject to the foregoing, this Agreement will be binding upon and inure in its entirety to the benefit of any successors permitted in accordance with this section.
C: 9.5|Amendments to this Agreement.|Any amendments to this Agreement will be made in writing (whereby any electronic form of text signed electronically by the authorized representatives also satisfies the requirements of written form under this Agreement). With regard to the SLS, the current version on the website applies (i.e., amendments of the SLS do not require the Customer&rsquo;s consent, unless the amendment would result in a significant reduction in the scope of the Services). Notwithstanding the foregoing, Hoshii reserves the right to amend this Agreement at any time by notifying the Customer (e.g., by e-mail). If the Customer does not object (by e-mail) within thirty (30) days after the notification, the Customer is deemed to have agreed to the changes.
C: 9.6|Force majeure.|If the Provider is prevented or delayed from performing any of its obligations under this Agreement due to circumstances beyond its reasonable control, including, but not limited to, natural disasters, pandemics, acts of government or regulatory authorities, strikes or other labor disputes, war, civil unrest, acts of terrorism, fire, embargoes, shortages in supply, or delays caused by third-party suppliers due to any such events, the Provider shall be excused from such performance for the duration of the event causing the prevention or delay. The Provider shall use all reasonable efforts to mitigate the impact of such events and to resume performance as soon as reasonably possible, provided that no such event shall excuse the Customer from making payments due under this Agreement.
C: 9.7|Applicable Law and Jurisdiction.|This Agreement and any other agreements in connection with the Services will in all respects be governed by, construed and enforced in accordance with the laws of Switzerland (without regard to conflict of law principles or international treaties that would result in the application of any law other than Swiss law). All disputes arising out of or in connection with this Agreement will be subject to the exclusive jurisdiction of the state courts of Z&uuml;rich, Switzerland.
"""

SLS = """
H2: 1. Introduction
C: 1.1||These SLS outline the availability, processing times, maintenance and support for the Services provided by Hoshii; in particular the Hoshii Platform. Any terms defined in Hoshii&rsquo;s [Master Subscription Agreement](msa.html) (&ldquo;MSA&rdquo;) and used in these SLS have the same meaning.
H2: 2. Our Commitment, Service Plans
C: 2.1||While we strive to deliver a seamless user experience and minimize service disruptions, occasional malfunctions or interruptions may occur despite our efforts. Our team is dedicated to promptly addressing any issues to ensure reliable service. Please note that these Service Level Specifications (SLS) as specified below are indicative and do not confer warranty rights.
C: 2.2||Customers may choose enhanced service levels through available service plans. The Provider reserves the right to amend, modify, or update such service plans from time to time at its sole discretion. Notwithstanding the foregoing, during the term of the Agreement, any amendments thereto shall not materially and adversely affect the Customer&rsquo;s rights or benefits under the existing service plans.
H2: 3. Service Availability and Uptime
C: 3.1|Service Hours.|The Hoshii Platform is available 24/7, except during scheduled maintenance periods between 00:00 and 04:00 Central European Time (CET) (&ldquo;Scheduled Maintenance&rdquo;) or other planned maintenance for updates, backups, or system optimization to ensure reliability, security, and performance. Unforeseen issues requiring immediate attention (&ldquo;Emergency Maintenance&rdquo;) may also occur. Hoshii will notify the Customer of Emergency Maintenance as soon as reasonably practicable.
C: 3.2|Availability.|Hoshii aims to ensure that the Hoshii Platform is available for at least 99.5% of the operating time (&ldquo;Uptime&rdquo;), on a yearly basis. Uptime commitment excludes downtime caused by (i) Scheduled Maintenance, (ii) Emergency Maintenance, (iii) Customer-side issues (e.g. network failure, incorrect configurations), (iv) third-party service failures (e.g. cloud provider outages) or force majeure events (disruptions beyond Hoshii&rsquo;s control like natural disasters, cyberattacks, etc.).
H2: 4. Support and Response Times
C: 4.1|Support Hours.|Support is available Monday&ndash;Friday, 08:00&ndash;12:00 and 13:30&ndash;17:00 CET.
C: 4.2|Issue Response Times.|Inquiries from paying Customers are categorized as listed in the table below. Troubleshooting is typically conducted through bugfix releases or other suitable methods. Resolution time is measured from when Hoshii receives the inquiry to when a fix or workaround is deployed, resolving the issue.
H2: 5. Updates, upgrades
C: 5.2|Issue Response Times.|Inquiries from paying Customers are categorized as listed in the table below. Troubleshooting is typically conducted through bugfix releases or other suitable methods. Resolution time is measured from when Hoshii receives the inquiry to when a fix or workaround is deployed, resolving the issue.
H2: 6. Limitation of Liability
C: 6.1||Updates and upgrades will be made available from time to time by the Provider to Customer. The Provider will inform the Customer of updates and upgrades.
C: 6.2||Unless otherwise specified in the Agreement or, if applicable, the service plan, updates and upgrades are subject to additional charges. Software patches and bug fixes are free of charge. Customer shall implement updates that are free of charge within 3 months of being made available. If the Customer fails to apply updates within this 3-month period, any additional work required by the Provider to address the late update will incur an extra fee.
H2: 7. Hourly Rate
C: 7.1||Unless otherwise defined in the Order Form, Hoshii&rsquo;s hourly rate is CHF&nbsp;200.00.
H2: 8. Contact for Support
P: For support, contact [support@hoshii.ai](mailto:support@hoshii.ai).
"""


FAQ = """
INDEX: Product &amp; how it works | Connected systems &amp; integrations | Security &amp; data | Getting started &amp; pricing
H2: Product &amp; how it works
H3: What is Hoshii?
P: Hoshii is the AI&#8209;native inbox for B2B operations. Our agents read what arrives in your team&rsquo;s shared mailboxes: orders, RFQs, complaints, chasers, plain questions. They reach into the systems the answers live in: your ERP, your CRM, your price lists, your files. They draft the reply that fits that customer, prepare the entry your ERP needs, and handle the repetitive work in between. Your team approves, adjusts or overrides. Your systems stay the record; Hoshii is where the work gets done.
H3: Who is Hoshii for?
P: B2B teams whose day arrives by email. Order desks and customer service, sales and account management, finance and accounts receivable, and the contract and legal side. Most of our customers are wholesalers, manufacturers and distributors in the DACH region, where a shared inbox is still where the work starts.
H3: Does Hoshii replace my team?
P: No. Hoshii takes the repetitive work so your team can get ahead of it. There is always a human in the loop: our agents prepare the work, your team approves, adjusts or overrides it. It takes work off your team, not decisions away from them.
H3: What happens when Hoshii gets something wrong?
P: Nothing reaches a customer or one of your systems without your approval. Your team corrects it before it goes out, and every correction teaches the agent through Continuous Learning, so the same mistake does not come back, and you can watch that happen in the autonomy figures in Analytics. You stay in control. AI can make mistakes, so always double check.
H3: Which channels and formats can Hoshii handle?
P: Email and whatever is attached to it: PDFs, Excel sheets, scans, plus voicemails, WhatsApp messages and photographs of handwritten notes. Whatever channel or format the work arrives in, Hoshii reads it and turns it into a structured task.
H3: Which languages does Hoshii understand?
P: Hoshii works out what a message means in any language and any phrasing, German, French, Italian and English included. Your customers never have to change how they write.
H3: What is the Unibox?
P: One shared workspace where every channel arrives as a structured task with an owner, a status and a deadline. Build personal views to work the way you like, and see where everything stands at a glance.
H3: Does Hoshii read my private inbox?
P: Shared stays shared, private stays private. Hoshii works in the mailboxes you point it at. Your personal mailbox stays yours. Nothing is read from it and nothing in it is visible to colleagues, until you choose to bring a specific thread into the Unibox.
H3: What are your agents?
P: An agent is a teammate you scope to one kind of work: order entry, quote follow&#8209;up, complaint triage, chasing unconfirmed orders. It works in the Unibox alongside the people doing the same job: picking up what arrives, preparing it, handing it over for approval.
P: Each one has its own level of autonomy, so an agent you have come to trust runs further ahead than one you added last week, and each learns from the corrections made to its own work. You add agents as you need them rather than switching everything on at once.
H3: What can the chat do for me?
P: Ask your own operation a question and get an answer out of your own data. Chat reaches the same connected systems our agents use, so &ldquo;which orders are still unconfirmed?&rdquo;, &ldquo;what did we quote this customer last time?&rdquo; or &ldquo;why is this delivery late?&rdquo; get answered from your ERP and your inbox instead of sending you looking. It runs inside Hoshii: what you ask and what it reads never leave your company.
H3: Can my team collaborate in Hoshii?
P: Yes. Comment on any task and @mention anyone, including colleagues who do not use Hoshii, and they can reply from their own inbox. Inviting your whole company to collaborate is free, so there is no more forwarding threads back and forth.
H3: What does Analytics show me?
P: Analytics is your read on how the operation actually runs: the mix of what arrives, where work is piling up and on whom, which customers or product lines cause the most rework, and how close each kind of task is to running on its own. It also points at what to fix next: the exception that keeps recurring and deserves a rule, the request type worth handing over.
H3: Can Hoshii run fully autonomously?
P: Autonomy is a spectrum, not a switch. Every kind of work sits somewhere between fully manual and fully autonomous, and it moves as Hoshii learns. We aim for 95% handled autonomously, with your team holding the judgment calls.
H3: How is Hoshii different from a chatbot or a generic AI assistant?
P: Hoshii is not a chat window. It is a workspace wired into your systems and your team&rsquo;s rules: it reads real inbound work, prepares finished entries and replies, and routes tasks to owners with deadlines. What comes out is operational work waiting for approval, not a conversation you then have to act on.
H3: We already use Microsoft Copilot. Why Hoshii?
P: Copilot helps one person write faster. Hoshii runs your team&rsquo;s work: shared tasks, context pulled from your systems, and numbers for the whole operation. Same budget, different job.
H2: Connected systems &amp; integrations
H3: What can Hoshii connect to?
P: Whatever your answers live in. Hoshii is live with 20+ ERP systems across DACH wholesale, manufacturing and distribution, and there are 1,300+ connectors for the systems around them: CRM, accounting, ticketing, spreadsheets, file shares. If a system has an interface, Hoshii can reach it.
H3: Do we need to connect our other systems?
P: No, you do not have to. Hoshii works from day one with just your mailbox: reading, sorting, drafting, following up. Still, the more context it has, the better it gets, so add your CRM, your calendar or your folders read&#8209;only whenever you want that context on your tasks. Connecting your ERP is what turns a draft into a finished entry, so it is worth doing early, but it is built in parallel and nothing waits on it.
H3: Which ERP systems does Hoshii work with?
P: Hoshii is live with 20+ ERP systems across DACH wholesale, manufacturing and distribution. If yours is not connected yet, Hoshii can connect to any ERP with an interface.
H3: What if my ERP is custom or in&#8209;house?
P: That is fine. A custom or in&#8209;house ERP connects through the Hoshii CDK (Connector Developer Kit) over a REST API, SFTP or Computer Use. You or your IT partner build the connection with whichever method fits, with no off&#8209;the&#8209;shelf integration required.
H3: What is the difference between a REST API and an SFTP integration?
P: Two ways to connect, depending on your system. REST is real&#8209;time and two&#8209;way: Hoshii reads and writes live, which suits systems with a modern interface. SFTP is file&#8209;based: structured files are dropped and collected on a schedule, which suits systems without a live API. For systems with no interface at all, Computer Use (Alpha) works the screen directly.
H3: What is the Hoshii CDK?
P: The Connector Developer Kit: the toolkit for connecting any ERP to Hoshii, over REST, SFTP or Computer Use. Your team or your IT partner builds the connection with it, and there is no plumbing left for you to maintain afterwards.
H3: Who builds the ERP connection?
P: Whoever you would rather have build it. Your own IT team can, with the CDK. So can your ERP provider or your IT consultant, who may already be a Hoshii partner, or can become one. And if you would rather not touch it at all, we will build it with you.
H3: Does Hoshii replace my ERP?
P: No. Your ERP stays your system of record. Hoshii is the layer above it, handling the journey from an inbound message to a clean, structured entry.
H3: How is Hoshii different from OCR or EDI tools?
P: OCR only extracts text. EDI only works when a customer sends a structured format. Hoshii reads unstructured messages across every channel, works out what is being asked, applies your team&rsquo;s rules, and prepares both the entry and the reply. That covers the cases OCR and EDI cannot: the email with three changes buried in it, the handwritten order, the &ldquo;urgent&rdquo; that means Friday.
H2: Security &amp; data
H3: Where is my data hosted?
P: Hoshii is built in Switzerland and hosted in the EU. Your data is processed in EU data centres and never leaves the EU.
H3: Is Hoshii GDPR&#8209;compliant?
P: Yes. Hoshii is GDPR&#8209;compliant, and a Data Processing Agreement (DPA) is available on request.
H3: Do you use my data to train AI models?
P: No. Your data is never used to train third&#8209;party models.
H3: What about SOC 2 and ISO 27001?
P: Hoshii is GDPR&#8209;compliant today, and SOC 2 and ISO 27001 audits are in progress. We are happy to share our current security documentation on request.
H2: Getting started &amp; pricing
H3: Can I set Hoshii up myself?
P: Yes. Sign in with Gmail or Outlook, point Hoshii at the mailboxes you want it working in, and it starts preparing what arrives. There is no implementation project and no migration. The one part that can involve someone else is the ERP connection, and even that your own IT team can build with the CDK rather than wait on us.
H3: How long does it take to get started?
P: Two parts, running in parallel. Signing in takes minutes: single sign&#8209;on with the mailbox you already use, no migration, no new address, and replies still go out from yours. Your team can work in Hoshii the same morning. The ERP connection is the longer half: often days with an ERP we already know, up to about six weeks with one that is new to us.
H3: Do you onboard and train our team?
P: You do not need us in order to start, because the Unibox is built to be picked up without training. When you want it, hands&#8209;on onboarding is there, and it is usually worth taking: adopting Hoshii is more a change in how the desk works than a change of software. As your team works, Hoshii learns your rules and settles into the way you already operate.
H3: Does my team have to change how they work?
P: No. The work keeps arriving in the inbox they already use, and that is where Hoshii starts, preparing each message before anyone opens it. When the team wants more overview, the Unibox is there: one shared inbox with owners, statuses and deadlines.
H3: What does it cost?
P: We quote per workspace, against how much lands in the inbox, how many inboxes it covers and which systems Hoshii writes into. Users are unlimited on every quote, so inviting your whole company to comment and weigh in costs nothing. The work itself is metered in credits, with an allowance we size to an average month with you. [How pricing works](pricing.html) sets out what moves the number.
H3: How do I get started?
P: Sign in and point Hoshii at one mailbox; you will see what it does with real work inside the hour. If you would rather be walked through it, book a demo and bring a real order, and we will show you exactly what our agents do with it, live, in 30 minutes.
CLOSER: Still holding a question this page did not answer?|Talk to sales|demo.html
"""


# Same portal and EU1 region as the partner form. Booking runs through a
# HubSpot form rather than the meetings scheduler.
DEMO = """
TEAM:
PERSON: Daniel Nydegger|Head of GTM||daniel-nydegger
PERSON: Jo&euml;l Heller|GTM Executive||joel-heller
PERSON: Philipp Kuprecht|GTM Executive||philipp-kuprecht
ENDTEAM:
CHECKS:
CHECK: Tell us what your inbox does to your week.
CHECK: Watch Hoshii run one of your own real messages.
CHECK: Leave with your price and your setup time.
ENDCHECKS:
BELT: Trusted by 500+ B2B operations teams|casadelvino,staempfli,chiefs,stutzer,igp,schuetzengarten,egger,safruits
ASIDE:
RAW:           <div class="doc__embed doc__embed--form">
RAW:             <div id="demo-form"></div>
RAW:             <script charset="utf-8" src="https://js-eu1.hsforms.net/forms/embed/v2.js"></script>
RAW:             <script>
RAW:               (function () {
RAW:                 var target = document.getElementById('demo-form');
RAW:                 if (!window.hbspt) {
RAW:                   target.innerHTML =
RAW:                     '<p class="doc__standin">The form did not load. Email ' +
RAW:                     '<a href="mailto:contact@hoshii.ai?subject=Book%20a%20demo">contact@hoshii.ai</a>' +
RAW:                     ' and we will find you a slot.</p>';
RAW:                   return;
RAW:                 }
RAW:                 hbspt.forms.create({
RAW:                   region: 'eu1',
RAW:                   portalId: '143412715',
RAW:                   formId: '4d222eb0-c951-4ddb-8951-f0df5c6f598e',
RAW:                   target: '#demo-form'
RAW:                 });
RAW:               })();
RAW:             </script>
RAW:           </div>
AFTER:
H2: Nobody leaves this call without a price.
PAIR:
AGENDA:
SLOT: 0&ndash;10|We start with you|What you are trying to fix, what you expect from this, and one real message out of your inbox to work with.
SLOT: 10&ndash;20|We run it live|What it reads, what it looks up, what it drafts, and exactly what it would post to your ERP.
SLOT: 20&ndash;30|Systems and numbers|What connecting yours takes, your price at your volume, and what changes for your team on Monday.
ENDAGENDA:
ENDPAIR:
"""


# Same portal, same EU1 region as the meetings embed on the demo page. The form
# id is the only thing still to fill in.
ABOUT = """
STATS:
STAT: Z&uuml;rich|Where we are built
STAT: 500+|B2B operations teams
STAT: 20+|ERP systems connected
STAT: 4|Languages handled
ENDSTATS:
H2: Empowering humans to do more.
P: We are on a mission to put AI in people&rsquo;s hands, so they can stop drowning in manual, repetitive work and spend their day on what actually matters: customers, judgement and growth.
P: Hoshii was founded on one conviction: the inbox was never built to run a business, and the people running theirs out of one deserve a real workspace.
H2: Built close to the work.
P: Hoshii is headquartered in Z&uuml;rich. Before this we built software at some of the world&rsquo;s largest technology and pharmaceutical companies; now we build for the businesses that keep goods moving. What we share is a respect for the unglamorous work, and the conviction that it deserves better software.
TEAM:
PERSON: Jiir Awdir|Co&#8209;founder &amp; CEO|The inbox is where B2B commerce actually happens. That is where the work belongs.|
PERSON: Ayoub Chouak|Co&#8209;founder &amp; CTO|Reliability first. An order desk cannot run on something that works most of the time.|
PERSON: Chihiro Okuyama|Co&#8209;founder &amp; CAIO|Models are the easy part. Earning the right to act on somebody&rsquo;s orders is the work.|
ENDTEAM:
H2: Where we are going.
P: Order processing was the first thing worth automating because it is the most painful. It is not the last. Every skill after it takes the same route: surfaced by the work itself, agreed with your team, then built.
CLOSER: Want to build this with us?|See open roles|careers.html
"""


PARTNERS = """
PROPS:
PROP: Bring Hoshii to your customers, integrated with the ERP and systems you already support.|You keep the relationship and the implementation. We never sell around you.
PROP: Connect any system through our CDK, so your customers stay on the stack they know.|REST where there is an API, SFTP where there is not, Computer Use where there is no interface at all.
PROP: Grow recurring revenue while we handle the AI heavy lifting in the background.|You build the connector once. It serves every client you have on that system.
ENDPROPS:
H2: Who this is for
PANELS:
PANEL: ERP vendors and integrators|Your customers are already asking what AI does for their order desk. Hoshii is the part that reads the mail and prepares the entry; your ERP stays the system of record.|prof-leads.jpg|rgba(120, 150, 170, 0.22)
PANEL: Agencies and IT consultancies|You are already the people they call when the order desk is drowning. Now there is something to deliver, not another process workshop.|prof-sales.jpg|rgba(214, 150, 90, 0.24)
ENDPANELS:
H2: What it takes
P: One connector, built with the Hoshii CDK. We are live with 20+ ERP systems already, so if yours is one of them there may be nothing to build at all. No certification to sit, no minimum to commit to: one system and one client is enough to start.
ASIDE:
RAW:         <div class="doc__embed doc__embed--form">
RAW:           <div id="partner-form"></div>
RAW:           <script charset="utf-8" src="https://js-eu1.hsforms.net/forms/embed/v2.js"></script>
RAW:           <script>
RAW:             (function () {
RAW:               var target = document.getElementById('partner-form');
RAW:               // Safety net: if the embed script is blocked, the reserved space
RAW:               // carries a working route rather than sitting empty.
RAW:               if (!window.hbspt) {
RAW:                 target.innerHTML =
RAW:                   '<p class="doc__standin">The form did not load. Tell us about your system and your customers at ' +
RAW:                   '<a href="mailto:partners@hoshii.ai?subject=Hoshii%20partnership">partners@hoshii.ai</a>' +
RAW:                   ' and we will come straight back to you.</p>';
RAW:                 return;
RAW:               }
RAW:               hbspt.forms.create({
RAW:                 region: 'eu1',
RAW:                 portalId: '143412715',
RAW:                 formId: '7c390eb1-8b4e-4e79-a072-386017d1c38e',
RAW:                 target: '#partner-form'
RAW:               });
RAW:             })();
RAW:           </script>
RAW:         </div>
"""


# Five of the six portraits exist; Kim's is a monogram until a photo lands.
# LinkedIn URLs are not in yet -- see the note in the handover rather than
# guessing at a real person's profile.
CAREERS = """
CTA: See open roles|#find-your-role
H2: How we work.
VALUES:
VALUE: Ownership|Run your area like it&rsquo;s yours.|You own outcomes, not busywork. On a small team, real responsibility lands on you from week one.
VALUE: Direct &amp; kind|Say it straight.|We give and take honest feedback early. It is faster, and it is how we get better, without the politics.
VALUE: Ship, then refine|Less process, more shipping.|We would rather put something real in front of customers and improve it than polish in private for months.
VALUE: Close to the work|Build for the order desk.|Every role talks to the people who actually use Hoshii. We solve real operational problems, not hype.
ENDVALUES:
H2: Meet the people building Hoshii.
TEAM:
PERSON: Daniel Nydegger|Head of GTM|If you cannot say what it does in one sentence, you do not understand it yet.|daniel-nydegger
PERSON: Jo&euml;l Heller|GTM Executive|My job is making sure customers feel the difference on day one.|joel-heller
PERSON: Philipp Kuprecht|GTM Executive|Every account is somebody’s working day, not a line in a pipeline.|philipp-kuprecht
PERSON: Francesco Intoci|Founding Software Engineer|We build the unglamorous infrastructure so the magic looks effortless.|francesco-intoci
PERSON: Antonio Stano|Founding Software Engineer||antonio-stano
PERSON: Alexander Sucur|Founder&rsquo;s Associate|Whatever moves us to the next milestone, that is my to&#8209;do list.|alexander-sucur
ENDTEAM:
H2: Join early enough to shape it.
P: We are a small team in Z&uuml;rich, and you would be early: your work genuinely shapes the product, the culture, and the company.
H2: Find your role.
P: Browse every open position and apply in a couple of clicks. New roles are posted here as we grow.
JOBS:
JOB: Forward Deployed Software Engineer|Z&uuml;rich|https://join.com/companies/hoshii/16577727-forward-deployed-software-engineer?pid=d73d1a20e99ab4ced633
JOB: Account Executive|Z&uuml;rich|https://join.com/companies/hoshii/16599890-account-executive?pid=d73d1a20e99ab4ced633
ENDJOBS:
CLOSER: Nothing here fits, but you think you should be here anyway?|Write to us|mailto:jobs@hoshii.ai
"""


# Seeded with what actually exists. HubSpot's blog holds one untouched
# placeholder draft, so there are no articles to list yet -- adding one is a
# single ENTRY line.
RESOURCES = """
FILTERS: Everything | Operations | Industry | AI &amp; Automation | Product
ENTRIES:
ENTRY: AI &amp; Automation|What Happens When an AI Agent Reads Your Customer Orders|Your team already knows the inbox is the problem. Here is what actually happens when an AI agent takes over the order flow, step by step, from email to ERP.|18 June 2026 &middot; 5 min|post-agent|https://www.hoshii.ai/blog-posts/what-happens-when-an-ai-agent-reads-your-customer-orders
ENTRY: Industry|How B2B Wholesale Actually Works in 2026|Digital transformation has reshaped how businesses talk about operations. It has not changed where most B2B orders actually arrive.|15 June 2026 &middot; 5 min|post-inbox|https://www.hoshii.ai/blog-posts/how-b2b-wholesale-actually-works-in-2026-(it-still-starts-in-an-inbox)
ENTRY: Product|Partnership Announcement: CSB&#8209;System x Hoshii|How Hoshii and CSB&#8209;System bring email order processing directly into the ERP.|12 June 2026 &middot; 5 min|post-cost|https://www.hoshii.ai/blog-posts/partnership-announcement-csb-system-x-hoshii
ENTRY: Industry|How Order Errors Drive Customer Churn in Wholesale Distribution|Why 75% of B2B buyers consider switching suppliers after repeated order mistakes, and how to stop the pattern.|10 June 2026 &middot; 6 min|post-inbox|https://www.hoshii.ai/blog-posts/how-order-errors-drive-customer-churn-in-wholesale-distribution
ENTRY: Operations|The Hidden Cost of Manual Order Processing in B2B|Most operations teams know manual order processing takes time. Few have counted what it costs. Here is what a typical day adds up to.|4 June 2026 &middot; 6 min|post-cost|https://www.hoshii.ai/blog-posts/the-hidden-cost-of-manual-order-processing-in-b2b
ENDENTRIES:
EMPTY: Nothing under that filter yet.
P: Looking for the answers rather than the reading? [Questions](faq.html) covers how Hoshii works, what it connects to and where your data lives. The [privacy policy](policies/privacy-policy.html) and the [subscription agreement](policies/msa.html) are the documents worth having open before you commit.
CLOSER: Rather see it running on your own mail than read about it?|Book a demo|demo.html
"""


CUSTOMERS = """
BELT: |casadelvino,staempfli,chiefs,stutzer,igp,schuetzengarten,egger,safruits
STATS:
STAT: 500+|teams running Hoshii
STAT: 20+|ERP systems written into
STAT: 4|languages handled
STAT: 100+|orders a day at the largest
ENDSTATS:
H2: Customers, on camera
CAMS:
CAM: wistia|213shm0tsd|Max Schwarz AG|Thomas Locher|Head of Sales|A night of Swiss&#8209;German voicemails, ERP&#8209;ready before the workday starts|customers/max-schwarz.html
CAM: wistia|l3tbbb0g61|Adank Davos AG|Marc Adank|Business Owner|Phone and PDF orders land in the ERP without the retyping|
CAM: wistia|fgphaw74q0|Marinello &amp; Co. AG|Max Marinello|Business Owner|Inbound orders handled, so the team can face customers instead of a keyboard|
ENDCAMS:
H2: Case studies
FEATS:
FEAT: stutzer|logo-stutzer.svg|Stutzer Service AG|Food &amp; beverage|2026|High-volume, multilingual order processing on Microsoft Dynamics|Over 100 orders a day, in German, French and Thai, typed and handwritten, prepared for Dynamics automatically.|Microsoft Dynamics|customers/stutzer-service.html
FEAT: egger|logo-egger.png|Egger Gem&uuml;sebau AG|Food &amp; beverage|2025|Voicemail and PDF orders, straight into the CSB ERP|Orders arrive by voicemail and PDF, often out of hours. They reach CSB System without anyone listening and retyping.|CSB System|customers/egger-gemuesebau.html
ENDFEATS:
CLOSER: Bring your most complex order. We will show you what happens to it.|Book a demo|demo.html
"""


CASE_STUTZER_SERVICE = """
SHOT: cover-stutzer.jpg|A Thai curry with rice and basil, plated
P: At Stutzer Service AG, order processing is a highly operational, fast-moving core activity. With more than 100 orders per day, handled by a team of over 15 people, the organisation processes a large and diverse volume of incoming orders every day.
P: Unlike highly standardised order environments, much of this work does not start in the ERP system itself. Orders arrive in many different formats: unstructured documents, handwritten notes, scanned PDFs, emails, and mixed attachments. Content varies significantly in layout and completeness and is submitted in multiple languages, including **German, French, and Thai, both typed and handwritten**.
P: Before any ERP process can begin, these orders must be interpreted, understood, and manually prepared, a step that is time-consuming and **heavily dependent on individual experience**.
P: To manage this complexity at scale, Stutzer Service AG uses Hoshii operationally in its daily order processing.
P: Hoshii is currently connected to their **Microsoft Dynamics Navision** environment via SFTP, where it prepares and transfers structured order data directly into the ERP.
P: Incoming documents are automatically read and understood, including unstructured layouts, handwritten content, and multilingual input. Relevant information such as articles, quantities, delivery details, and customer references is extracted and prepared in a consistent format for ERP processing.
LIFT: The team continues to work in its familiar tools and communication channels. Orders arrive as they always have.
P: In the background, Hoshii reduces manual interpretation effort and translates complexity into structured data that can be reliably processed in the ERP.
P: As a result, Stutzer Service AG is able to handle very high order volumes more effectively. **Processing becomes faster and more consistent**, dependency on individual knowledge is reduced, and operational know-how is captured centrally rather than residing only with experienced employees. This also makes onboarding new team members significantly easier.
P: Until the end of 2025, parts of the organisation operated under the name George Weiss Lebensmittel AG. On 1 January 2026, George Weiss Lebensmittel AG merged with Stutzer Service AG. Hoshii supported this transition by integrating the newly added team in Villars alongside the existing team in Fahrenweid, ensuring consistent order processing across locations during the merger.
P: Looking ahead, Stutzer Service AG is preparing the next step in its ERP setup. In April, the connection will move from Microsoft Dynamics Navision to **Microsoft Dynamics 365 Business Central**, replacing the SFTP integration with a REST API-based connection. This will enable deeper integration, faster data exchange, and access to additional functionality as the organisation continues to scale.
CLOSER: Bring your most complex order. We will show you what happens to it.|Book a demo|../demo.html
"""

CASE_EGGER_GEMUESEBAU = """
SHOT: cover-egger.jpg|Five of the Egger Gem&uuml;sebau team standing in one of their cabbage fields
P: At Egger Gemüsebau, the ERP system has been the backbone of operational workflows for many years. As a vegetable producer with high order volumes and a fast-paced daily business, core processes run through **CSB System**: reliably, in a structured way, and deeply embedded in day-to-day operations.
P: At the same time, much of the daily work does not start in the ERP system, but before it. Orders arrive via **voicemail or as PDF attachments** by email, often **outside of office hours**. These messages must be listened to, read, interpreted, and manually transferred into the system. This step between communication and ERP is time-consuming and error-prone, and this is exactly where the greatest leverage was identified.
P: As part of a pilot project, Egger Gemüsebau therefore began using Hoshii operationally for the first time.
P: In practical terms, **voicemail and PDF orders are automatically captured**, understood in context, and prepared in a way that allows seamless transfer into the CSB system.
P: Employees continue to work in their familiar communication environment. Orders arrive as they always have, by phone or email. In the background, Hoshii takes over the content processing, identifies relevant information such as items, quantities, and delivery dates, and transfers this data in a structured form to CSB. The operational process therefore starts exactly where it belongs, in the ERP system, **without manual listening, typing, or forwarding**.
LIFT: Communication is no longer a preliminary manual effort, but an integrated part of the ERP process.
P: As a result, day-to-day work at Egger Gem&uuml;sebau changes noticeably. Workflows become more consistent, **response times shorter**, and the team is relieved, especially during periods of high order volume.
P: Based on the success of this pilot project, Hoshii and CSB System have now entered into a **partnership**. The goal is to systematically bring AI-driven communication processing into the CSB ecosystem and make it accessible to additional CSB customers. Insights from the project with Egger Gemüsebau flow directly into the expansion of the integration and the further development of standardised use cases.
CLOSER: Bring your most complex order. We will show you what happens to it.|Book a demo|../demo.html
"""

CASE_MAX_SCHWARZ = """
VIDEO: wistia|213shm0tsd|Thomas Locher of Max Schwarz AG on running Hoshii
P: At Max Schwarz AG, a significant share of daily orders is placed by phone and received as **voicemails outside of business hours**. Especially overnight, a high volume of customer orders accumulates before the working day even begins.
P: These voicemails are typically recorded in **Swiss German, often spoken quickly and informally**. Before any ERP process can start, messages must be listened to carefully, understood correctly, and manually transferred into the system. This task is time-consuming and places a high dependency on employees who are fluent in Swiss German.
P: To handle this workload more efficiently, Max Schwarz AG uses Hoshii in daily operations. Hoshii automatically transcribes Swiss-German voicemails and makes the content available in **clear Standard German**. Based on this transcription, order information is structured and prepared for processing in **Fruchtmanager**, the company&rsquo;s ERP system.
P: Orders that previously required repeated listening and interpretation are now available as written, structured information **as soon as the team starts its day**. This significantly reduces manual effort and accelerates order processing.
PULL: The 2 to 3 hours a day we used to process orders have been cut in half. New joiners also have impact significantly faster.|Thomas Locher|Head of Sales, Max Schwarz AG|thomas-locher.jpg
P: A key benefit is the **relief for employees who are not fluent in Swiss German**. Instead of relying on dialect comprehension, they can work directly with Standard German transcriptions, ensuring consistent understanding and reliable order handling across the team.
P: As a result, Max Schwarz AG is able to process high overnight voicemail volumes more efficiently, **start ERP workflows earlier in the day**, and reduce dependency on individual language skills. Communication is transformed into structured input for the ERP, enabling smoother operations and more balanced workload distribution within the team.
CLOSER: Bring your most complex order. We will show you what happens to it.|Book a demo|../demo.html
"""


CASE_MARINELLO = """
VIDEO: wistia|fgphaw74q0|Max Marinello of Marinello &amp; Co. AG on running Hoshii
P: Max Marinello on how Hoshii handles inbound orders, so the team can spend its attention on customers instead of retyping what customers already sent.
"""

CASE_ADANK_DAVOS = """
VIDEO: wistia|l3tbbb0g61|Marc Adank of Adank Davos AG on running Hoshii
P: Marc Adank on turning phone and PDF orders into clean ERP entries, without anyone in the middle retyping them.
"""


# Transferred from Pricing_Hoshii_August_2026_v2.xlsx, sheets "Pricing
# Overview" and "Credit Mechanics". Deliberately excluded: the internal credit
# strategy notes, the PROPOSED 12x balance cap, and the three OPEN DECISIONS.
# See the handover note rather than assuming they were missed.
# Not published. The tier table below was transferred from
# Pricing_Hoshii_August_2026_v2.xlsx and went up as three fixed plans at
# 149/299/499 EUR a month. It came down on 2026-08-27 because it contradicted
# how Hoshii is actually sold: entry deals land at 5-8k and grow from there, so
# the top published tier annualised to less than an entry deal, and every
# prospect who read it anchored 3-5x below the real number. Kept here because
# the packaging logic is correct and a self-serve tier is a plausible future;
# only the publishing was wrong. Not referenced by CONTENT, so it emits nothing.
PRICING_INTERNAL = """
TOGGLE:
PLANS:
PLAN: Workspace Launch||Prove it on one inbox.|149|178.80|&euro;1,788|2,000 credits a month ~ One shared inbox, two personal ~ Unlimited users ~ Partner ERPs and inbound webhook ~ Email support
PLAN: Workspace Team|Most teams start here|Open it up to the whole desk.|299|358.80|&euro;3,588|3,500 credits a month ~ Unlimited inboxes ~ Single sign&#8209;on ~ Team analytics ~ Priority support
PLAN: Workspace Automate||Let the agents finish the work.|499|598.80|&euro;5,988|5,000 credits a month ~ System write&#8209;back ~ ERP order processing skill ~ Custom security paperwork ~ Named contact
ENDPLANS:
P: All prices in EUR, excluding VAT. Monthly billing costs 20% more on the base price, so committing annually saves 16.7%. Add&#8209;ons are always billed monthly at flat prices, and the uplift never applies to them.
H2: What each plan includes
TABLE: |Launch|Team|Automate
GROUP: Postings and inboxes
ROW: Credits per month|2,000|3,500|5,000
ROW: Shared inboxes included|1|2|2
ROW: Personal inboxes included|2|5|5
ROW: Maximum inboxes in total|3|unlimited|unlimited
GROUP: Access and users
ROW: Users, platform access|unlimited|unlimited|unlimited
ROW: Users, view&#8209;only analytics|unlimited|unlimited|unlimited
ROW: Single sign&#8209;on|No|Yes|Yes
ROW: Email encryption|Yes|Yes|Yes
ROW: EU hosting|Yes|Yes|Yes
ROW: Custom security paperwork|No|No|Yes
GROUP: What the agents can do
ROW: Agents|unlimited|unlimited|unlimited
ROW: Context search|Yes|Yes|Yes
ROW: Email drafting|Yes|Yes|Yes
ROW: Confirmation mail|Yes|Yes|Yes
ROW: AI chat|Yes|Yes|Yes
ROW: Knowledge base|Yes|Yes|Yes
ROW: Self learning|Yes|Yes|Yes
ROW: ERP order processing|No|No|Yes
GROUP: Systems and insight
ROW: Partner ERPs|Yes|Yes|Yes
ROW: Inbound webhook|Yes|Yes|Yes
ROW: System write&#8209;back|No|No|Yes
ROW: Inbox analytics|Yes|Yes|Yes
ROW: Team analytics|No|Yes|Yes
ROW: Supported languages|25+|25+|25+
ROW: Support|Email|Priority|Individual
ENDTABLE:
H2: Add&#8209;ons
P: Added or removed in any month, billed monthly on every plan including annual commitments.
TABLE: |Launch|Team|Automate
ROW: Additional shared inbox, per month|n/a|&euro;49|&euro;49
ROW: Additional personal inbox, per month|&euro;19|&euro;19|&euro;19
ROW: Credit pack, 1,000 credits per month|&euro;30|&euro;30|&euro;30
ENDTABLE:
P: Launch caps total connected inboxes at three. The personal inbox add&#8209;on rebalances the mix inside that cap; it does not raise it.
H2: How credits work
P: One credit is &euro;0.03 on every plan and every add&#8209;on. Your allowance is issued on your subscription anniversary and unused credits roll over, so a quiet month builds a balance that carries a busy one. Size your packs to an average month, not a peak.
NOTE: Run low and you get a warning in the cockpit and by email; hit zero without auto top&#8209;up and there is a three business day grace window, long enough for SEPA to settle. Past that the platform still runs. Classification, routing and analytics carry on. Only the actions that spend credits pause.
H2: What each action costs
TABLE: Action|Credits|At &euro;0.03
ROW: Context lookup|7|&euro;0.21
ROW: ERP order processing|20|&euro;0.60
ROW: Email drafting|3|&euro;0.09
ROW: Confirmation mail|2|&euro;0.06
ENDTABLE:
P: ERP order processing does not include a separate context lookup: the 20 credits cover the full order flow. Chat with your data is priced individually.
CLOSER: Not sure which tier your volume lands in? We will work it out with you.|Talk to sales|demo.html
"""


PRICING = """
P: No table, because a desk taking forty orders a day and one taking four hundred are not the same work. We look at your inbox, then quote.
H2: What moves the number
PROPS:
PROP: Volume|How much lands, and in what form. The first thing we measure.
PROP: Inboxes|How many the desk runs, shared and personal.
PROP: Systems|Reading your ERP is included. Writing into it is scoped.
PROP: Paperwork|A standard security review is included. A custom one is scoped.
ENDPROPS:
H2: What you never pay for
CHECKS:
CHECK: Users. Invite the whole company, at no extra cost.
CHECK: All 25+ languages, and every system Hoshii reads from.
CHECK: Corrections. Being wrong once is how it learns, not an extra.
ENDCHECKS:
H2: How it starts
P: Read only. Hoshii prepares and proposes, and nothing leaves until someone approves it. Your own analytics then show which processes are worth automating, and the quote moves with the ones you pick. You never buy an automation you have not watched work.
P: The work itself is metered in credits, on a monthly allowance we size to an average month with you. Unused credits roll over.
CLOSER: Bring one real inbox. We will work out the number with you.|Book a demo|demo.html
"""

CONTENT = {
    "pricing": (
        PRICING,
        "How Hoshii is priced: on what your inbox handles, not per seat. What sets the number, what every workspace includes, and how credits work.",
        "Priced on what your inbox actually does, not on how many people look at it.",
    ),
    "stutzer-service": (
        CASE_STUTZER_SERVICE,
        "Over 100 orders a day in German, French and Thai, typed and handwritten, prepared for Microsoft Dynamics automatically.",
        "Over 100 orders a day in German, French and Thai, typed and handwritten, prepared for Microsoft Dynamics automatically.",
    ),
    "egger-gemuesebau": (
        CASE_EGGER_GEMUESEBAU,
        "Orders arrive by voicemail and PDF, often out of hours, and reach CSB System without anyone listening and retyping.",
        "Orders arrive by voicemail and PDF, often out of hours, and reach CSB System without anyone listening and retyping.",
    ),
    "max-schwarz": (
        CASE_MAX_SCHWARZ,
        "A night of dialect voicemails is written, structured and waiting in Fruchtmanager when the team arrives.",
        "A night of dialect voicemails is written, structured and waiting in Fruchtmanager when the team arrives.",
    ),
    "privacy-policy": (
        PRIVACY,
        "How Hoshii collects, uses and protects personal data on hoshii.ai.",
        "How we handle personal data on this website, and the rights you have over it.",
    ),
    "cookies-policy": (
        COOKIES,
        "Which cookies hoshii.ai sets, what they do, and how to turn them off.",
        "Which cookies this site sets, what they are for, and how to switch them off.",
    ),
    "imprint": (
        IMPRINT,
        "Legal notice for Hoshii AG, Zürich, Switzerland.",
        "The entity behind this website, and the terms on which its content is published.",
    ),
    "msa": (
        MSA,
        "The Master Subscription Agreement governing use of the Hoshii Platform.",
        "The agreement governing use of the Hoshii Platform and the services around it.",
    ),
    "about": (
        ABOUT,
        "Hoshii is the AI-native inbox for B2B operations, built in Z\u00fcrich. Our mission, our founders and where we are going.",
        "The inbox was never built to run a business. We are building the workspace for "
        "the people who run theirs out of one.",
    ),
    "customers": (
        CUSTOMERS,
        "How B2B operations teams run their order desks on Hoshii, in their own words, on live order volume.",
        "They all started in the same place: an inbox nobody could get to the bottom of. "
        "Here is what changed, in their own words.",
    ),
    "resources": (
        RESOURCES,
        "Guides, answers and documents on running a B2B order desk with Hoshii.",
        "Guides, answers and the documents worth reading before you commit to anything.",
    ),
    "careers": (
        CAREERS,
        "Open roles at Hoshii, the AI-native inbox for B2B operations, in Zurich.",
        "We are building the AI-native inbox for B2B operations. If you want to ship something used every day by the teams that keep goods moving, build it with us.",
    ),
    "partners": (
        PARTNERS,
        "Bring AI-driven order processing to your customers, powered by you. For ERP vendors, integrators and agencies.",
        "For the ERP vendors, integrators and agencies who already own the systems their customers run on.",
    ),
    "demo": (
        DEMO,
        "Book 30 minutes with Hoshii. Bring one real order and watch it run.",
        "Thirty minutes. One real message out of your own inbox, run live in front of you.",
    ),
    "faq": (
        FAQ,
        "Answers on how Hoshii works, what it connects to, where your data lives and how to start.",
        "How Hoshii works, what it connects to, where your data lives, and what it takes to start.",
    ),
    "sls": (
        SLS,
        "Availability, support hours and response times for the Hoshii Platform.",
        "Availability, maintenance windows, support hours and response times.",
    ),
}



def faq_schema(block):
    """FAQPage JSON-LD, derived from the FAQ block itself.

    Built from the same source the page renders, because schema that disagrees
    with the visible text is a penalty rather than a boost. Answers may run to
    more than one paragraph, so they are joined.
    """
    pairs, q, a = [], None, []
    for raw in block.strip().split("\n"):
        line = raw.strip()
        if line.startswith("H3: "):
            if q:
                pairs.append((q, " ".join(a)))
            q, a = line[4:], []
        elif line.startswith("P: ") and q:
            a.append(line[3:])
        elif line.startswith("H2: ") and q:
            pairs.append((q, " ".join(a)))
            q, a = None, []
    if q:
        pairs.append((q, " ".join(a)))

    def plain(t):
        t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
        return html.unescape(t)

    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": plain(q),
                "acceptedAnswer": {"@type": "Answer", "text": plain(a)},
            }
            for q, a in pairs
        ],
    }
    body = json.dumps(data, ensure_ascii=False, indent=6).replace("\n", "\n    ")
    return f'    <script type="application/ld+json">\n    {body}\n    </script>\n'


def build_main(slug, title, stand, body):
    # A page can decline the standfirst: pricing is called Pricing and says the
    # rest with the plans themselves. An empty one emits no element, rather than
    # an empty paragraph holding open the space it would have filled.
    stand = (
        f'\n          <p class="doc__standfirst">{stand}</p>' if stand.strip() else ""
    )
    if slug in BOOK:
        head, sep, rest = body.partition("<!--HEAD-->")
        if not sep:
            head, rest = "", body
        left, _, rest = rest.partition("<!--ASIDE-->")
        aside, _, after = rest.partition("<!--AFTER-->")
        block = (
            '\n      <div class="book__more guides">\n'
            '        <div class="doc__inner doc__body">\n'
            + after.rstrip()
            + "\n        </div>\n      </div>"
        ) if after.strip() else ""
        return BOOK_MAIN.format(
            title=title, stand=stand, body=left.rstrip(),
            aside=aside.strip(), after=block,
        )
    if slug in CASE:
        return CASE_MAIN.format(title=title, stand=stand, body=body.rstrip())
    if slug not in SPLIT:
        return PLAIN_MAIN.format(title=title, stand=stand, body=body)
    head, sep, rest = body.partition("<!--HEAD-->")
    if not sep:
        head, rest = "", body
    left, _, rest = rest.partition("<!--ASIDE-->")
    aside, _, after = rest.partition("<!--AFTER-->")
    block = (
        '\n      <div class="doc__band doc__band--after guides">\n'
        '        <div class="doc__inner doc__body">\n'
        + after.rstrip()
        + "\n        </div>\n      </div>"
    ) if after.strip() else ""
    return SPLIT_MAIN.format(
        title=title,
        stand=stand,
        head=head.rstrip(),
        body=left.rstrip(),
        aside=aside.strip(),
        after=block,
    )


def patch_index_head(origin, staging):
    """Bring index.html's head into line with the chosen origin.

    index.html is the one page this script does not emit, so its canonical,
    og:url and robots meta were outside the origin switch entirely -- meaning a
    --staging build noindexed all sixteen generated pages and left the homepage
    crawlable, canonicalised to the live domain. That is the exact failure the
    staging flag exists to prevent, so the head is patched in place. The body
    and the design stay hand-written; only these three lines are owned here.
    """
    path = SITE / "index.html"
    page = path.read_text(encoding="utf-8")
    before = page

    # The homepage's own links are normalised by the same function that does
    # the generated pages, so the two layouts cannot drift apart.
    page = clean_urls(page, ".")
    # And the one path that lives in JS, where the post-pass cannot see it.
    page = page.replace("'assets/pattern.svg'", "'/assets/pattern.svg'")

    page = re.sub(r'(<link rel="canonical" href=")[^"]*(")',
                  lambda m: m.group(1) + origin + m.group(2), page, count=1)
    page = re.sub(r'(<meta property="og:url" content=")[^"]*(")',
                  lambda m: m.group(1) + origin + m.group(2), page, count=1)
    page = re.sub(r'(<meta property="og:image" content=")[^"]*(")',
                  lambda m: m.group(1) + origin + "assets/img/hero-slot.jpg" + m.group(2),
                  page, count=1)

    # The robots meta is present only while staging, and sits immediately
    # before the canonical so the head reads the same way as a generated page.
    page = re.sub(r'[ \t]*<meta name="robots"[^>]*>\n', "", page)
    if staging:
        page = page.replace(
            '    <link rel="canonical"',
            '    <meta name="robots" content="noindex, nofollow" />\n'
            '    <link rel="canonical"', 1)

    if page != before:
        path.write_text(page, encoding="utf-8")
    return page != before


def write_sitemap(origin):
    """sitemap.xml from DOCS, so a new page cannot be forgotten in it.

    NOINDEX pages are excluded by construction rather than by remembering: they
    carry a robots meta telling crawlers to skip them, and listing them in the
    sitemap would contradict it.
    """
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    entries = [(".", origin)] + [
        (slug, origin + url_path_for(folder, slug))
        for folder, slug, title in DOCS
        if slug not in NOINDEX
    ]
    missing = [k for k, _ in entries if k not in SITEMAP]
    if missing:
        raise SystemExit(
            "no sitemap metadata for: " + ", ".join(missing)
            + "\nadd them to SITEMAP, or add the slug to NOINDEX to leave them out"
        )
    for key, loc in entries:
        lastmod, changefreq, priority = SITEMAP[key]
        rows += ["  <url>", f"    <loc>{loc}</loc>",
                 f"    <lastmod>{lastmod}</lastmod>",
                 f"    <changefreq>{changefreq}</changefreq>",
                 f"    <priority>{priority}</priority>", "  </url>"]
    rows.append("</urlset>")
    (SITE / "sitemap.xml").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(entries)


ROBOTS_LIVE = """User-agent: *
Allow: /

# Answer engines and AI crawlers are welcome: being cited is the point.
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: {origin}sitemap.xml
"""

# A staging host that gets crawled competes with the real one for the same
# content, and the crawler picks the winner, not you. Belt and braces: this
# plus the noindex meta on every page.
ROBOTS_STAGING = """# Staging. Not the live site.
User-agent: *
Disallow: /
"""


def main():
    ap = argparse.ArgumentParser(description="Build the Hoshii site.")
    ap.add_argument("--origin", default=ORIGIN,
                    help="absolute origin for canonicals, og:url and the sitemap "
                         "(default: %(default)s)")
    ap.add_argument("--staging", action="store_true",
                    help="noindex every page and disallow all crawling: for any "
                         "host that is not the real domain")
    args = ap.parse_args()

    origin = args.origin if args.origin.endswith("/") else args.origin + "/"
    global STAGING
    STAGING = args.staging

    for folder, slug, title in DOCS:
        block, desc, stand = CONTENT[slug]
        # Each page is <dir>/index.html so its URL carries no extension.
        # customers.html becomes customers/index.html and the case studies stay
        # at customers/<slug>/index.html, which nests without colliding.
        pdir = page_dir_for(folder, slug)
        out = SITE / pdir
        out.mkdir(parents=True, exist_ok=True)
        up = ".." if folder != "." else "."
        dm = "../" if folder != "." else ""
        page = PAGE.format(
            main_cls=("book-page" if slug in BOOK else "doc"),
            robots=(
                '    <meta name="robots" content="noindex, nofollow" />\n'
                if STAGING
                else '    <meta name="robots" content="noindex, follow" />\n'
                if slug in NOINDEX
                else ""
            ),
            title=title,
            head_title=HEAD_TITLES.get(slug, title),
            site=origin,
            path=url_path_for(folder, slug),
            desc=desc,
            stand=stand,
            up=up,
            lg="" if folder == "policies" else ("../policies/" if folder != "." else "policies/"),
            dm=dm,
            wide=("" if slug not in WIDE else " doc--wide")
            + (" doc--split" if slug in SPLIT else ""),
            header=(FULL_HEADER if slug in FULL_NAV else MINIMAL_HEADER).format(
                up=up, dm=dm, cta=HEADER_CTA.get(slug, "Book a demo")
            ),
            script=(MENU_JS if slug in FULL_NAV else "")
            + (FILTER_JS if slug == "resources" else "")
            + (TOGGLE_JS if "TOGGLE:" in block else "")
            + (COUNT_JS if "STAT:" in block else "")
            + PATTERN_JS.replace("{up}", up),
            v=CSS_V,
            head=faq_schema(FAQ) if slug == "faq" else "",
            main=build_main(slug, title, stand, render(block, fold=slug == "faq", up=up)),
        )
        (out / "index.html").write_text(clean_urls(page, folder), encoding="utf-8")
        print(f"/{pdir}/  {len(page) // 1024}KB")

    touched = patch_index_head(origin, STAGING)
    print(f"index.html   head {'rewritten' if touched else 'already in step'}")
    robots = ROBOTS_STAGING if STAGING else ROBOTS_LIVE.format(origin=origin)
    (SITE / "robots.txt").write_text(robots, encoding="utf-8")
    n = write_sitemap(origin)
    print(f"sitemap.xml  {n} urls")
    print(f"robots.txt   {'STAGING (disallow all)' if STAGING else 'live'}")
    print(f"origin       {origin}")
    if STAGING:
        print("\nStaging build: every page carries noindex,nofollow and robots.txt")
        print("disallows all crawling. Do not deploy this to the real domain.")


if __name__ == "__main__":
    main()
