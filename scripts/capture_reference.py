"""Capture reference canvas screenshots for calibrating the CV state-reader.

Launches a visible, persistent browser session against tetr.io and takes a
burst of screenshots over a play window. You should manually start a solo
round (40 LINES or ZEN) and play a few pieces during that window so we get
frames with real board state, not just an empty board / menu.

Run with: uv run python scripts/capture_reference.py
"""

import time
from pathlib import Path

from tetris_bot.interface.browser import launch_session
from tetris_bot.interface.capture import (
    FOREGROUND_CANVAS_SELECTOR,
    GAME_CANVAS_SELECTOR,
    capture_canvas,
)

OUT_DIR = Path(__file__).resolve().parents[1] / ".reference_captures"
PLAY_SECONDS = 90
CAPTURE_INTERVAL = 5


def main():
    session = launch_session()
    print("Session ready. Start a 40 LINES or ZEN round and play.")
    print(f"Capturing every {CAPTURE_INTERVAL}s for {PLAY_SECONDS}s.")

    elapsed = 0
    frame = 0
    while elapsed < PLAY_SECONDS:
        time.sleep(CAPTURE_INTERVAL)
        elapsed += CAPTURE_INTERVAL
        frame += 1
        bg_path = capture_canvas(session.page, GAME_CANVAS_SELECTOR, OUT_DIR / f"bg_{frame:02d}.png")
        msg = f"[{elapsed}s] captured {bg_path.name}"
        try:
            fg_path = capture_canvas(session.page, FOREGROUND_CANVAS_SELECTOR, OUT_DIR / f"fg_{frame:02d}.png", timeout_ms=2000)
            msg += f", {fg_path.name}"
        except Exception:
            msg += " (fg not visible, skipped)"
        print(msg)

    session.close()
    print(f"\nDone. {frame} frame pairs saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
