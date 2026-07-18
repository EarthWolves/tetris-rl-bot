"""Canvas screenshot capture.

tetr.io renders through PixiJS onto two stacked canvases, `#pixi` (game
scene) and `#pixi-fg` (foreground layer). There is no DOM-level board state
to scrape, so board/piece state is read from pixels sampled off these
canvases (see calibration.py / vision.py once calibrated).
"""

from pathlib import Path

from playwright.sync_api import Page

GAME_CANVAS_SELECTOR = "#pixi"
FOREGROUND_CANVAS_SELECTOR = "#pixi-fg"


def capture_canvas(page: Page, selector: str, out_path: Path, timeout_ms: float | None = None) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {"path": str(out_path)}
    if timeout_ms is not None:
        kwargs["timeout"] = timeout_ms
    page.locator(selector).screenshot(**kwargs)
    return out_path
