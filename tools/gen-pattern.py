#!/usr/bin/env python3
"""Generate the Hoshii pattern as a deterministic, tileable SVG.

Two shapes, and only two, both cut from the same square on the same 45-degree
diagonal:

    * the half square -- a right triangle, legs on two edges, hypotenuse on the
      cell diagonal. Two quarters of the cell.
    * the notched square -- the whole cell with a V bitten out of one edge, its
      apex at the cell centre. Three quarters of the cell.

Placement is random, cell by cell. A mirrored version existed briefly -- one
quadrant drawn and reflected across both axes -- and the trouble with real symmetry
is that the eye finds the axis and then reads the whole field as one motif rather
than as a texture. Random placement has no axis to find, which is what keeps it
reading as a ground.

The fades are glassy, not linear. Two things make them so: the alpha follows a
smoothstep curve rather than a straight ramp, so the transition has a soft shoulder
at both ends instead of starting and stopping abruptly; and the colour lightens as
it thins, the way light does coming through glass rather than paint simply running
out. A dithered version existed briefly -- turbulence added to the alpha and
hard-thresholded -- and reads as print grain, which is a different thing.

    python3 tools/gen-pattern.py            # writes assets/pattern.svg
    python3 tools/gen-pattern.py --seed 7   # a different draw
"""

import argparse
import pathlib
import random

OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "pattern.svg"

# A small tile, because it is repeated as an element rather than painted as a
# background. Stretching one 12x8 tile to cover a layer made the module as wide as
# the layer over twelve -- 121px on the pitch slab against the 32px it used to be.
# Six by four tiles instead, laid out on a grid at a stated module size.
COLS, ROWS = 6, 4
CELL = 120          # cell edge
# Measured off the reference: its channel is about 19% of the cell edge. At 12%
# the shapes of neighbouring cells met at their corners and the field read as
# pinwheels rather than as tiles on a grid.
GUTTER = 23
SEED = 3

# The ramp, deep to pale, measured off the reference.
DEEP = "#055836"
MID = "#3f8a68"
PALE = "#a4c9b8"

# Share of cells left empty. The reference leaves roughly one in eight bare,
# which is what stops the grid reading as a checkerboard.
EMPTY_RATE = 0.12

# Stops per gradient. A two-stop linear ramp has a visible start: the eye finds
# the point where the fade begins. Six stops on a smoothstep curve do not.
STOPS = 6
# One gradient per tone-and-axis pair, shared by every cell that wants it, rather
# than one per cell. 84 unique gradients of six stops is 588 nodes a tile -- fine
# as a painted image, and the reason the pattern could not become real elements
# without adding several thousand nodes to the document. Eighteen shared ones cost
# 126, and a cell referencing a shared gradient looks identical to one referencing
# its own.
SHARED_FAR = 0.78
# How far the tone lifts toward white across the fade. This is the glassy part --
# without it the shape reads as paint thinning out, with it as light through
# glass. Past about 0.45 the pale tiles wash out entirely.
LIFT = 0.34

# Triangles carry the field; the notched square is the accent that gives it mass.
# Two to one keeps the heavier shape from closing the pattern up.
FORMS = ["half", "notch"]
FORM_WEIGHTS = [2, 1]



def lift(hex_colour, amount):
    """Mix a hex colour toward white. Done on the encoded sRGB values, which is
    what a CSS or SVG gradient interpolates on, so the ramp this produces matches
    what the renderer would do between the same two stops."""
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    m = lambda c: round(c + (255 - c) * amount)
    return "#%02x%02x%02x" % (m(r), m(g), m(b))


def glass(tone, far):
    """A gradient's stops: alpha down a smoothstep, colour up toward white."""
    out = []
    for i in range(STOPS):
        t = i / (STOPS - 1)
        # smoothstep: flat at both ends, steepest in the middle.
        a = 1 - t * t * (3 - 2 * t)
        out.append(
            '<stop offset="%s" stop-color="%s" stop-opacity="%s"/>'
            % (round(t * far, 4), lift(tone, LIFT * t), round(a, 4))
        )
    return "".join(out)


def half(s, rot):
    """Right triangle, two quarters of the cell, right angle in one corner."""
    return [
        [(0, 0), (s, 0), (0, s)],
        [(s, 0), (s, s), (0, 0)],
        [(s, s), (0, s), (s, 0)],
        [(0, s), (0, 0), (s, s)],
    ][rot]


def notch(s, rot):
    """The cell with a V bitten out of one edge, apex at the centre. Three quarters
    of the cell. rot names the notched edge: 0 right, 1 bottom, 2 left, 3 top."""
    h = s / 2
    return [
        [(0, 0), (s, 0), (h, h), (s, s), (0, s)],
        [(s, 0), (s, s), (h, h), (0, s), (0, 0)],
        [(s, s), (0, s), (h, h), (0, 0), (s, 0)],
        [(0, s), (0, 0), (h, h), (s, 0), (s, s)],
    ][rot]


SHAPES = {"half": half, "notch": notch}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--cols", type=int, default=COLS)
    ap.add_argument("--rows", type=int, default=ROWS)
    args = ap.parse_args()

    rnd = random.Random(args.seed)
    mod = CELL + GUTTER
    w, h = args.cols * mod, args.rows * mod

    AXES = [(0, 0, 1, 1), (1, 0, 0, 1), (0, 1, 1, 0), (1, 1, 0, 0),
            (0, 0, 1, 0), (0, 0, 0, 1)]
    TONES = [("d", DEEP), ("m", MID), ("p", PALE)]

    # The shared set, named by tone and axis so a cell can pick one.
    grads = []
    for tk, tone in TONES:
        for ai, (x1, y1, x2, y2) in enumerate(AXES):
            grads.append(
                '    <linearGradient id="hp-%s%d" x1="%d" y1="%d" x2="%d" y2="%d">%s'
                "</linearGradient>" % (tk, ai, x1, y1, x2, y2, glass(tone, SHARED_FAR))
            )

    shapes = []
    n = 0
    for row in range(args.rows):
        for col in range(args.cols):
            if rnd.random() < EMPTY_RATE:
                continue
            n += 1

            form = rnd.choices(FORMS, weights=FORM_WEIGHTS, k=1)[0]
            rot = rnd.randrange(4)

            # Where this cell sits on the ramp. A mild bias toward pale, not a
            # square one: squaring left almost nothing deep and the field read as
            # a wash. The reference carries roughly a quarter deep tiles.
            depth = rnd.random() ** 1.25
            tk = "d" if depth > 0.62 else ("m" if depth > 0.3 else "p")
            ai = rnd.randrange(6)

            pts = SHAPES[form](CELL, rot)
            ox, oy = col * mod, row * mod
            poly = " ".join("%g,%g" % (ox + x, oy + y) for x, y in pts)
            shapes.append(
                '    <polygon points="%s" fill="url(#hp-%s%d)"/>' % (poly, tk, ai)
            )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
        'width="%d" height="%d" role="img" aria-label="Hoshii pattern">\n'
        "  <defs>\n%s\n  </defs>\n%s\n</svg>\n"
        % (w, h, w, h, "\n".join(grads), "\n".join(shapes))
    )
    OUT.write_text(svg)
    print("%s  %d cells of %d  %.1f KB"
          % (OUT.name, n, args.cols * args.rows, len(svg) / 1024))


if __name__ == "__main__":
    main()
