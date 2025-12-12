from __future__ import annotations

from pathlib import Path

# NOTE:
# This conftest.py is written into the ephemeral run directory mounted into the runner container.
# It overrides pytest-playwright fixtures (page/context/browser) to support remote browser
# connection via Playwright Browser Server (WebSocket) when PLAYWRIGHT_WS_ENDPOINT is set.

CONFTEST_CONTENT = r"""
import os

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def _pw():
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="session")
def browser(_pw):
    ws = os.getenv("PLAYWRIGHT_WS_ENDPOINT")
    browser_name = (os.getenv("PLAYWRIGHT_BROWSER", "chromium") or "chromium").strip().lower()

    browser_type = getattr(_pw, browser_name, _pw.chromium)

    if ws:
        # Remote mode: connect to Playwright Browser Server
        b = browser_type.connect(ws)
        yield b
        b.close()
        return

    # Local fallback
    headless = (os.getenv("PLAYWRIGHT_HEADLESS", "1") or "1").lower() not in ("0", "false", "no")
    b = browser_type.launch(headless=headless)
    yield b
    b.close()


@pytest.fixture()
def context(browser):
    ctx = browser.new_context()
    yield ctx
    ctx.close()


@pytest.fixture()
def page(context):
    p = context.new_page()
    yield p
    p.close()
"""


def write_conftest(run_dir_abs: Path) -> Path:
    run_dir_abs.mkdir(parents=True, exist_ok=True)
    path = run_dir_abs / "conftest.py"
    path.write_text(CONFTEST_CONTENT, encoding="utf-8")
    return path
