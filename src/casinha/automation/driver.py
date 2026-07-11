"""
Chrome WebDriver factory and shared element helpers.

Centralises driver creation (headless options, window size).  Interactions in
the flow modules locate elements with these thin helpers and pace themselves
with time.sleep(), mirroring the timings that proved reliable against the
postback-heavy government portals.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from typing import Callable

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


# ---------------------------------------------------------------------------
# Result type returned by every automation flow
# ---------------------------------------------------------------------------

@dataclass
class AutomationResult:
    success: bool
    message: str
    screenshot: bytes | None = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Driver factory
# ---------------------------------------------------------------------------

def _find_binary(*names: str) -> str | None:
    """Return the first executable found on PATH from *names*, else None."""
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def make_driver(
    *,
    headless: bool = True,
    width: int = 1200,
    height: int = 768,
    x: int = 22,
    y: int = 47,
) -> WebDriver:
    """Return a configured Chrome/Chromium WebDriver instance.

    On Streamlit Cloud (and other Debian hosts) the browser is installed via
    ``packages.txt`` as ``chromium``/``chromium-driver``.  We point Selenium
    explicitly at those binaries when they exist; otherwise we fall back to
    Selenium Manager, which resolves a locally-installed Chrome for development.
    """
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")

    browser_path = _find_binary("chromium", "chromium-browser")
    if browser_path:
        opts.binary_location = browser_path

    driver_path = _find_binary("chromedriver")
    service = Service(executable_path=driver_path) if driver_path else None

    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_window_size(width, height)
    driver.set_window_position(x, y)
    return driver


# ---------------------------------------------------------------------------
# Element helpers
# ---------------------------------------------------------------------------

def find_id(driver: WebDriver, element_id: str) -> WebElement:
    """Locate an element by its id."""
    return driver.find_element(By.ID, element_id)


def find_xpath(driver: WebDriver, xpath: str) -> WebElement:
    """Locate an element by xpath."""
    return driver.find_element(By.XPATH, xpath)


def js_click(driver: WebDriver, element: WebElement) -> None:
    """Click *element* via JavaScript (bypasses overlapping-element issues)."""
    driver.execute_script("arguments[0].click();", element)


# ---------------------------------------------------------------------------
# Progress callback type alias
# ---------------------------------------------------------------------------

ProgressCallback = Callable[[str], None]
