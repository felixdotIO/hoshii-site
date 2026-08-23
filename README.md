# Hoshii — site

Static marketing site. No build step, no dependencies: `index.html`, `styles.css`,
`assets/`. Edit and reload.

## Run it

```bash
python3 -m http.server 4321
```

Then open http://localhost:4321/index.html.

Two caching traps, because `http.server` sends no cache headers:

- `styles.css` is versioned in the markup (`styles.css?v=NN`) — **bump it on every
  stylesheet change** or you will be looking at the old CSS.
- The browser caches `index.html` hard too. Load `index.html?r=N` with a fresh
  number to see markup changes.
- Images are cached by filename; renaming is the reliable bust.

## Sections, in page order

| Section | Class | Notes |
| --- | --- | --- |
| Announcement bar | `.announce` | Dismissible |
| Title bar | `.titlebar` | The window chrome **is** the nav |
| Hero | `.hero` | Photo in a retro-OS window frame |
| Client marquee | `.proof` | Track duplicated in JS, seamless `-50%` loop |
| Explainer slab | `.pitch` | Dark panel, two dialog renders as art |
| Quote | `.quote` | Narrowest column on the page |
| Sequence | `.steps` | Five steps, scroll-driven |

## Things that are load-bearing

**Hero framing.** `.hero__screen` holds a ratio rather than filling whatever the
fold leaves over. Sizing it to `100svh - reserve` produced a 2.86:1 screen on a
720px-tall laptop — a 218px crop that cut the tops of the subjects' heads off.
It now sits in a band: `max-height` keeps the client row inside the first screen,
`min-height` floors the crop at 1/2.7 of the width. `min-height` beats
`max-height` in CSS, which is what makes the floor hard. `--fold-reserve` is the
measured 263px of chrome above and below it — keep it in step with the
announcement bar, title bar, taskbar and `.proof`.

**Guide lines.** `.guides` draws a 1px rule down each edge of a band's column
plus a hairline where bands meet. Each band sets its own `--guide-col`, so the
rules step inward down the page: slab 94rem → quote 68rem → sequence 88rem. The
slab's rules sit *on* its edges; text bands inset their content from the rules,
because type clamped to a line reads like a mistake.

**The sequence is progressive enhancement.** The rail is built in JS and the tab
layout only engages once `.steps--tabs` is added. Without JS the five rows stay
stacked and readable, and every step remains in the document. All panels share
one grid cell so the container is as tall as the tallest and switching cannot
make the page jump; inactive panels hide with `visibility`, which keeps that
height and still removes them from the accessibility tree.

**Dialogs.** Two forms of the same window: `assets/img/dialog-*.png` (cropped
tight to the window — the source renders' glow and black ground caused a bright
rectangle and cross-bleed under `mix-blend-mode: lighten`, so they stack opaquely
now) and the CSS `.dlg` component used in the sequence. Bevels are two-tone,
light top-left and shadow bottom-right; a single border cannot express that,
which is why flat imitations look wrong.

## Assets

`assets/fonts/` holds Satoshi (Fontshare). Check the licence before making this
repo public or redistributing the files.
