import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time

def test_duckduckgo_search(status_updater):
    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ensure GUI is not displayed
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

    # Initialize WebDriver with options
    with webdriver.Chrome(options=chrome_options) as driver:
        try:
            status_updater.text('Navigating to DuckDuckGo...')
            driver.get("https://www.duckduckgo.com")
            assert "DuckDuckGo" in driver.title

            status_updater.text('Performing search operation...')
            search_box = driver.find_element("name", "q")
            search_box.clear()

            search_term = "selenium headless browser testing"
            search_box.send_keys(search_term)
            search_box.send_keys(Keys.RETURN)  # Simulate pressing the Enter key

            time.sleep(2)  # Wait a bit for the search results to load

            status_updater.text('Verifying search results...')
            assert search_term in driver.title

            return "Test passed: Search operation was successful."
        except AssertionError as error:
            return f"Test failed: {error}"

# Streamlit UI
st.title('Selenium Test on Streamlit')

# Placeholder for live updates
status_message = st.empty()

if st.button('Run Selenium Test'):
    result_message = test_duckduckgo_search(status_message)
    status_message.success(result_message)
