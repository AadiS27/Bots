"""Base page object with common Selenium utilities."""

from typing import Optional

from loguru import logger
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings


class BasePage:
    """
    Base page object with common Selenium operations.

    All page objects should inherit from this class and use explicit waits.
    """

    def __init__(self, driver: WebDriver):
        """
        Initialize base page.

        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.timeout = settings.EXPLICIT_TIMEOUT

    def wait_for_visible(self, locator: tuple[By, str], timeout: Optional[int] = None) -> WebElement:
        """
        Wait for element to be visible and return it.

        Args:
            locator: Tuple of (By.*, "selector")
            timeout: Optional custom timeout in seconds

        Returns:
            WebElement when visible

        Raises:
            TimeoutException: If element not visible within timeout
        """
        wait_timeout = timeout or self.timeout
        try:
            # Use shorter polling interval (0.2s instead of default 0.5s) for faster detection
            element = WebDriverWait(self.driver, wait_timeout, poll_frequency=0.2).until(
                EC.visibility_of_element_located(locator)
            )
            logger.debug(f"Element visible: {locator}")
            return element
        except TimeoutException:
            logger.error(f"Timeout waiting for element to be visible: {locator}")
            raise

    def wait_for_clickable(self, locator: tuple[By, str], timeout: Optional[int] = None) -> WebElement:
        """
        Wait for element to be clickable and return it.

        Args:
            locator: Tuple of (By.*, "selector")
            timeout: Optional custom timeout in seconds

        Returns:
            WebElement when clickable

        Raises:
            TimeoutException: If element not clickable within timeout
        """
        wait_timeout = timeout or self.timeout
        try:
            # Use shorter polling interval for faster detection
            element = WebDriverWait(self.driver, wait_timeout, poll_frequency=0.2).until(
                EC.element_to_be_clickable(locator)
            )
            logger.debug(f"Element clickable: {locator}")
            return element
        except TimeoutException:
            logger.error(f"Timeout waiting for element to be clickable: {locator}")
            raise

    def wait_for_presence(self, locator: tuple[By, str], timeout: Optional[int] = None) -> WebElement:
        """
        Wait for element to be present in DOM (not necessarily visible).

        Args:
            locator: Tuple of (By.*, "selector")
            timeout: Optional custom timeout in seconds

        Returns:
            WebElement when present

        Raises:
            TimeoutException: If element not present within timeout
        """
        wait_timeout = timeout or self.timeout
        try:
            # Use shorter polling interval for faster detection
            element = WebDriverWait(self.driver, wait_timeout, poll_frequency=0.2).until(
                EC.presence_of_element_located(locator)
            )
            logger.debug(f"Element present: {locator}")
            return element
        except TimeoutException:
            logger.error(f"Timeout waiting for element presence: {locator}")
            raise

    def click(self, locator: tuple[By, str], timeout: Optional[int] = None) -> None:
        """
        Wait for element to be clickable and click it.

        Args:
            locator: Tuple of (By.*, "selector")
            timeout: Optional custom timeout in seconds
        """
        element = self.wait_for_clickable(locator, timeout)
        element.click()
        logger.debug(f"Clicked element: {locator}")

    def type(self, locator: tuple[By, str], text: str, timeout: Optional[int] = None, clear_first: bool = True) -> None:
        """
        Wait for element to be visible and type text into it.

        Args:
            locator: Tuple of (By.*, "selector")
            text: Text to type
            timeout: Optional custom timeout in seconds
            clear_first: Whether to clear existing text first
        """
        element = self.wait_for_visible(locator, timeout)
        if clear_first:
            element.clear()
        element.send_keys(text)
        logger.debug(f"Typed into element: {locator}")

    def get_text(self, locator: tuple[By, str], timeout: Optional[int] = None) -> str:
        """
        Wait for element to be visible and return its text.

        Args:
            locator: Tuple of (By.*, "selector")
            timeout: Optional custom timeout in seconds

        Returns:
            Element text content
        """
        element = self.wait_for_visible(locator, timeout)
        text = element.text
        logger.debug(f"Got text from element {locator}: {text[:50]}...")
        return text

    def get_attribute(self, locator: tuple[By, str], attribute: str, timeout: Optional[int] = None) -> str:
        """
        Wait for element and return its attribute value.

        Args:
            locator: Tuple of (By.*, "selector")
            attribute: Attribute name
            timeout: Optional custom timeout in seconds

        Returns:
            Attribute value
        """
        element = self.wait_for_visible(locator, timeout)
        value = element.get_attribute(attribute)
        logger.debug(f"Got attribute '{attribute}' from element {locator}: {value}")
        return value or ""

    def exists(self, locator: tuple[By, str], timeout: int = 2) -> bool:
        """
        Check if element exists (with short timeout).

        Args:
            locator: Tuple of (By.*, "selector")
            timeout: Timeout in seconds (default: 2)

        Returns:
            True if element exists, False otherwise
        """
        try:
            self.wait_for_presence(locator, timeout)
            return True
        except TimeoutException:
            return False

    def find_elements(self, locator: tuple[By, str], timeout: Optional[int] = None) -> list[WebElement]:
        """
        Wait for at least one element and return all matching elements.

        Args:
            locator: Tuple of (By.*, "selector")
            timeout: Optional custom timeout in seconds

        Returns:
            List of WebElements (empty list if none found after timeout)
        """
        wait_timeout = timeout or self.timeout
        try:
            # Use shorter polling interval for faster detection
            WebDriverWait(self.driver, wait_timeout, poll_frequency=0.2).until(
                EC.presence_of_element_located(locator)
            )
            elements = self.driver.find_elements(*locator)
            logger.debug(f"Found {len(elements)} elements matching: {locator}")
            return elements
        except TimeoutException:
            logger.warning(f"No elements found matching: {locator}")
            return []

    def is_visible(self, locator: tuple[By, str]) -> bool:
        """
        Check if element is currently visible (no wait).

        Args:
            locator: Tuple of (By.*, "selector")

        Returns:
            True if visible, False otherwise
        """
        try:
            element = self.driver.find_element(*locator)
            return element.is_displayed()
        except NoSuchElementException:
            return False

    def scroll_to_element(self, locator: tuple[By, str], timeout: Optional[int] = None) -> WebElement:
        """
        Scroll to element and return it.

        Args:
            locator: Tuple of (By.*, "selector")
            timeout: Optional custom timeout in seconds

        Returns:
            WebElement after scrolling
        """
        element = self.wait_for_presence(locator, timeout)
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        logger.debug(f"Scrolled to element: {locator}")
        return element

    def switch_to_iframe(self, locator: tuple[By, str], timeout: Optional[int] = None) -> None:
        """
        Switch to iframe by locator.

        Args:
            locator: Tuple of (By.*, "selector")
            timeout: Optional custom timeout in seconds
        """
        wait_timeout = timeout or self.timeout
        # Use shorter polling interval for faster detection
        WebDriverWait(self.driver, wait_timeout, poll_frequency=0.2).until(
            EC.frame_to_be_available_and_switch_to_it(locator)
        )
        logger.debug(f"Switched to iframe: {locator}")

    def switch_to_default_content(self) -> None:
        """Switch back to main document from iframe."""
        self.driver.switch_to.default_content()
        logger.debug("Switched to default content")

