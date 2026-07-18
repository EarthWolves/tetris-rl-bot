"""Print decoded board/hold/next matrices for a captured screenshot.

Usage:
    uv run python scripts/print_state.py .reference_captures/bg_04.png
"""

import sys
from pathlib import Path

from tetris_bot.interface.vision import (
    decode_board_matrices,
    decode_hold_matrix,
    decode_next_matrices,
    decode_occupancy,
    extract_active_shape,
    format_matrix,
)


def main():
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/print_state.py <path/to/screenshot.png>")
        sys.exit(1)

    path = Path(sys.argv[1])

    print(f"===== {path.name} =====")

    print("\n-- occupancy (locked + active, 20x10) --")
    print(format_matrix(decode_occupancy(path)))

    locked, active = decode_board_matrices(path)
    shape = extract_active_shape(active)
    print("\n-- active piece compact shape --")
    print(format_matrix(shape) if shape else "(none)")

    hold_m = decode_hold_matrix(path)
    print("\n-- hold --")
    print(format_matrix(hold_m) if hold_m else "(empty)")

    print("\n-- next queue --")
    for i, m in enumerate(decode_next_matrices(path)):
        label = format_matrix(m).replace("\n", " / ") if m else "(empty)"
        print(f"  [{i}]: {label}")


if __name__ == "__main__":
    main()
