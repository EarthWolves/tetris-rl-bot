"""Calibration constants for reading tetr.io's board via pixel sampling.

Measured from a live screenshot at the 1280x800 viewport used by
browser.DEFAULT_VIEWPORT, against tetr.io's PixiJS-rendered client (see
CLAUDE.md for why this is pixel-sampling and not JS/DOM extraction). These
are empirical pixel measurements, not values from any tetr.io source. If
tetr.io changes its layout, or the viewport size changes, recalibrate by
capturing a fresh reference screenshot (scripts/capture_reference.py) and
re-deriving these constants against it.
"""

BOARD_ORIGIN_X = 526
BOARD_ORIGIN_Y = 172
CELL_SIZE = 22.9
BOARD_COLS = 10
BOARD_ROWS = 20

# Hue center (degrees, 0-360) for each piece's block color, sampled from
# locked (not actively-falling) blocks. The actively-falling piece renders
# brighter/more saturated but at the same hue, so classification is done by
# hue alone, not exact RGB or saturation/value.
PIECE_HUES = {
    "L": 22.8,  # orange
    "O": 47.9,  # yellow
    "S": 82.8,  # green
    "I": 158.0,  # teal/cyan
    "J": 250.0,  # blue
    "T": 305.9,  # purple
    "Z": 356.7,  # red
}

# A cell is "empty" if its HSV value (brightness) is below this. Empty cells
# and grid lines both sit well below this threshold; filled blocks (even
# shaded/locked ones) sit around 0.65-0.9.
EMPTY_VALUE_THRESHOLD = 0.35

# A cell is also "empty" if its HSV saturation is below this, regardless of
# brightness. Needed because the page background art (visible above the
# board's top border, where a piece can render during spawn) is desaturated
# (~0.06-0.09) but happens to land within ~1-12deg of a piece hue by pure
# coincidence - brightness alone isn't enough to reject it. Real piece
# colors are always highly saturated (~0.6-0.8).
MIN_SATURATION = 0.3

# Number of extra grid rows to sample above the visible board's row 0 when
# looking for the active piece. Pieces spawn partially above the visible
# border and fall into view over the first frame or two - without this, the
# active piece's shape reads truncated right after spawn. The locked stack
# never needs this (blocks only ever come to rest within the visible rows).
HIDDEN_ROWS_ABOVE = 2

# tetr.io renders the piece currently under player control brighter/more
# saturated than locked blocks of the same hue (measured: active ~0.89,
# locked ~0.62-0.72 across multiple frames, clean gap). A filled cell is
# "active" (not locked) if its HSV value is above this.
ACTIVE_VALUE_THRESHOLD = 0.8

# Canonical spawn-orientation shapes, one row-major binary matrix per piece
# letter. This is fixed game knowledge (guideline SRS spawn states), not
# something to re-derive from pixels each time: HOLD/NEXT previews always
# render a piece in its spawn orientation, so once pixel classification
# tells us *which* piece is in a slot, its shape follows deterministically.
# The active piece on the board is different - its rotation varies, so that
# shape must still be read from pixels (see vision.extract_active_shape).
PIECE_SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}

# HOLD box interior, in canvas pixel coordinates (below the "HOLD" label).
HOLD_BOX = (403, 195, 523, 249)

# NEXT queue box interior (below the "NEXT" label), divided evenly into
# NEXT_SLOT_COUNT vertically-stacked slots, one upcoming piece each.
NEXT_BOX_X = (766, 890)
NEXT_BOX_Y = (191, 536)
NEXT_SLOT_COUNT = 5
