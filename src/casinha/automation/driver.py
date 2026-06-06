"""
Chrome WebDriver factory and shared element helpers.

Centralises driver creation (headless options, window size).  Interactions in
the flow modules locate elements with these thin helpers and pace themselves
with time.sleep(), mirroring the timings that proved reliable against the
postback-heavy government portals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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

def make_driver(*, headless: bool = True, width: int = 1200, height: int = 768) -> WebDriver:
    """Return a configured Chrome WebDriver instance."""
    opts = Options()
    if headless:
        opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)
    driver.set_window_size(width, height)
    driver.set_window_position(22, 47)
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
