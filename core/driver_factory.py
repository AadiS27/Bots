"""WebDriver factory for creating configured Selenium drivers."""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver

from config import settings


def create_driver(headless: bool | None = None) -> WebDriver:
    """
    Create a configured Chrome WebDriver instance.

    Uses Selenium Manager (Selenium 4.15+) to automatically download and manage ChromeDriver.
    No manual driver setup required.

    Args:
        headless: Run in headless mode. If None, uses SELENIUM_HEADLESS from settings.

    Returns:
        Configured Chrome WebDriver instance
    """
    if headless is None:
        headless = settings.SELENIUM_HEADLESS

    # Configure Chrome options
    chrome_options = Options()

    if headless:
        chrome_options.add_argument("--headless=new")  # New headless mode (Chrome 109+)

    # Performance and stability options
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--window-size=1600,900")

    # Disable automation indicators
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Create service (Selenium Manager will handle driver download)
    service = Service()

    # Create driver
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Set timeouts
    driver.set_page_load_timeout(settings.PAGELOAD_TIMEOUT)

    return driver

