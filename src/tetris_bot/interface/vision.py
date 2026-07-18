"""Decode a captured board-canvas screenshot into logical board/hold/next state."""

import colorsys
from collections import Counter
from pathlib import Path

from PIL import Image

from tetris_bot.interface.calibration import (
    ACTIVE_VALUE_THRESHOLD,
    BOARD_COLS,
    BOARD_ORIGIN_X,
    BOARD_ORIGIN_Y,
    BOARD_ROWS,
    CELL_SIZE,
    EMPTY_VALUE_THRESHOLD,
    HIDDEN_ROWS_ABOVE,
    HOLD_BOX,
    MIN_SATURATION,
    NEXT_BOX_X,
    NEXT_BOX_Y,
    NEXT_SLOT_COUNT,
    PIECE_HUES,
    PIECE_SHAPES,
)

EMPTY = "."


def _hue_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _classify_pixel_v(rgb: tuple[int, int, int]) -> tuple[str | None, float]:
    """Classify a single pixel as (piece letter or None, HSV value)."""
    r, g, b = (c / 255 for c in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < EMPTY_VALUE_THRESHOLD or s < MIN_SATURATION:
        return None, v
    hue_deg = h * 360
    piece = min(PIECE_HUES, key=lambda p: _hue_distance(hue_deg, PIECE_HUES[p]))
    return piece, v


def _classify_pixel(rgb: tuple[int, int, int]) -> str | None:
    """Classify a single pixel as a piece letter, or None if empty/background."""
    return _classify_pixel_v(rgb)[0]


def _classify_cell(rgb: tuple[int, int, int]) -> str:
    return _classify_pixel(rgb) or EMPTY


def _classify_region(px, box: tuple[float, float, float, float], grid: int = 6) -> str | None:
    """Classify a rectangular region (e.g. a HOLD/NEXT slot) by sampling a
    grid of points inside it and taking the majority non-empty piece letter.
    Needed because a piece's shape rarely fills its whole slot bounding box,
    unlike board cells which are sampled one-per-cell."""
    x0, y0, x1, y1 = box
    votes: Counter[str] = Counter()
    for i in range(grid):
        for j in range(grid):
            x = int(x0 + (i + 0.5) * (x1 - x0) / grid)
            y = int(y0 + (j + 0.5) * (y1 - y0) / grid)
            piece = _classify_pixel(px[x, y][:3])
            if piece:
                votes[piece] += 1
    return votes.most_common(1)[0][0] if votes else None


def decode_board(image_path: Path) -> list[list[str]]:
    """Read a board screenshot into a BOARD_ROWS x BOARD_COLS grid of piece
    letters ('.' for empty)."""
    img = Image.open(image_path).convert("RGB")
    px = img.load()
    grid = []
    for row in range(BOARD_ROWS):
        row_cells = []
        for col in range(BOARD_COLS):
            cx = int(BOARD_ORIGIN_X + (col + 0.5) * CELL_SIZE)
            cy = int(BOARD_ORIGIN_Y + (row + 0.5) * CELL_SIZE)
            row_cells.append(_classify_cell(px[cx, cy]))
        grid.append(row_cells)
    return grid


def decode_board_matrices(image_path: Path) -> tuple[list[list[int]], list[list[int]]]:
    """Read the board into two binary (0/1) matrices: (locked, active).
    `locked` is the settled stack, BOARD_ROWS x BOARD_COLS. `active` marks
    only the piece currently under player control (brighter-rendered than
    locked blocks - see ACTIVE_VALUE_THRESHOLD), and is taller -
    (HIDDEN_ROWS_ABOVE + BOARD_ROWS) x BOARD_COLS - because a piece spawns
    partially above the visible board and falls into view over the first
    frame or two; active[HIDDEN_ROWS_ABOVE] aligns with locked[0]. A cell is
    never 1 in both within the visible region."""
    img = Image.open(image_path).convert("RGB")
    px = img.load()
    locked = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    active = [[0] * BOARD_COLS for _ in range(HIDDEN_ROWS_ABOVE + BOARD_ROWS)]
    for row in range(-HIDDEN_ROWS_ABOVE, BOARD_ROWS):
        for col in range(BOARD_COLS):
            cx = int(BOARD_ORIGIN_X + (col + 0.5) * CELL_SIZE)
            cy = int(BOARD_ORIGIN_Y + (row + 0.5) * CELL_SIZE)
            piece, v = _classify_pixel_v(px[cx, cy])
            if piece is None:
                continue
            if v >= ACTIVE_VALUE_THRESHOLD:
                active[row + HIDDEN_ROWS_ABOVE][col] = 1
            elif row >= 0:
                locked[row][col] = 1
    return locked, active


def decode_occupancy(image_path: Path) -> list[list[int]]:
    """Read the board into a single BOARD_ROWS x BOARD_COLS binary (0/1)
    occupancy matrix (locked stack + active piece combined, visible rows
    only - the active piece's hidden-row portion, if any, is dropped)."""
    locked, active = decode_board_matrices(image_path)
    return [
        [locked[r][c] | active[r + HIDDEN_ROWS_ABOVE][c] for c in range(BOARD_COLS)]
        for r in range(BOARD_ROWS)
    ]


def extract_active_shape(active: list[list[int]]) -> list[list[int]] | None:
    """Crop the active-piece matrix down to its minimal bounding box, i.e.
    just the piece's own shape independent of board position (and of
    whether part of it is still in the hidden spawn rows). None if no
    active piece is present in this frame."""
    rows = [r for r, row in enumerate(active) if any(row)]
    if not rows:
        return None
    cols = [c for c in range(len(active[0])) if any(active[r][c] for r in rows)]
    r0, r1 = min(rows), max(rows)
    c0, c1 = min(cols), max(cols)
    return [[active[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]


def decode_hold(image_path: Path) -> str | None:
    """Read the HOLD box. Returns a piece letter, or None if empty."""
    img = Image.open(image_path).convert("RGB")
    return _classify_region(img.load(), HOLD_BOX)


def decode_next_queue(image_path: Path) -> list[str | None]:
    """Read the NEXT queue box into NEXT_SLOT_COUNT upcoming piece letters,
    nearest-first."""
    img = Image.open(image_path).convert("RGB")
    px = img.load()
    x0, x1 = NEXT_BOX_X
    y0, y1 = NEXT_BOX_Y
    slot_h = (y1 - y0) / NEXT_SLOT_COUNT
    slots = []
    for i in range(NEXT_SLOT_COUNT):
        sy0 = y0 + i * slot_h
        sy1 = sy0 + slot_h
        slots.append(_classify_region(px, (x0, sy0, x1, sy1)))
    return slots


def decode_hold_matrix(image_path: Path) -> list[list[int]] | None:
    """Read the HOLD box as a canonical shape matrix. HOLD always shows a
    piece in spawn orientation, so once we know *which* piece (pixel
    classification), its shape is fixed game knowledge (PIECE_SHAPES) -
    unlike the active piece on the board, there's no rotation to read."""
    piece = decode_hold(image_path)
    return PIECE_SHAPES[piece] if piece else None


def decode_next_matrices(image_path: Path) -> list[list[list[int]] | None]:
    """Read the NEXT queue as canonical shape matrices, nearest-first."""
    return [PIECE_SHAPES[p] if p else None for p in decode_next_queue(image_path)]


def format_board(grid: list[list[str]]) -> str:
    return "\n".join("".join(row) for row in grid)


def format_matrix(matrix: list[list[int]]) -> str:
    return "\n".join("".join(str(v) for v in row) for row in matrix)
