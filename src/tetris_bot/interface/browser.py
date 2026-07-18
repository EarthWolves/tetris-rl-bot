"""Persistent Playwright browser session against tetr.io.

A persistent profile is required: a cold profile takes tetr.io's client
roughly 200s to boot before its network layer is interactive; a warm one
boots in ~15s. Always launch non-headless so the session is watchable.
"""

from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

TETRIO_URL = "https://tetr.io"
DEFAULT_PROFILE_DIR = Path(__file__).resolve().parents[3] / ".browser_profile"
DEFAULT_VIEWPORT = {"width": 1280, "height": 800}


@dataclass
class BrowserSession:
    playwright: Playwright
    context: BrowserContext
    page: Page

    def close(self) -> None:
        self.context.close()
        self.playwright.stop()


def launch_session(profile_dir: Path = DEFAULT_PROFILE_DIR) -> BrowserSession:
    profile_dir.mkdir(parents=True, exist_ok=True)
    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        str(profile_dir), headless=False, viewport=DEFAULT_VIEWPORT
    )
    page = context.pages[0] if context.pages else context.new_page()
    try:
        page.goto(TETRIO_URL, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        pass  # tetr.io keeps background network activity alive forever; harmless
    return BrowserSession(playwright=playwright, context=context, page=page)
