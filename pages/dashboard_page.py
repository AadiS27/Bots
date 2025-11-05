"""Dashboard page object for navigating to eligibility."""

from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from core.errors import PortalChangedError

from .base_page import BasePage


class DashboardPage(BasePage):
    """Page object for Availity dashboard navigation."""

    # Eligibility link from dashboard - multiple selectors to try
    ELIGIBILITY_LINK = (By.CSS_SELECTOR, "a[title='Eligibility and Benefits Inquiry']")
    ELIGIBILITY_LINK_ALT = (By.XPATH, "//a[contains(@href, 'eligibility') and contains(@title, 'Eligibility')]")
    ELIGIBILITY_PAGE_MARKER = (By.CSS_SELECTOR, "form, input")  # Generic marker - any form or input indicates we're on eligibility page

    def __init__(self, driver: WebDriver):
        """
        Initialize dashboard page.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def go_to_eligibility(self, skip_manual: bool = False) -> None:
        """
        Navigate to the Eligibility section.
        
        Args:
            skip_manual: If True, skip manual navigation wait (for subsequent requests)

        Raises:
            PortalChangedError: If navigation fails
        """
        try:
            if skip_manual:
                logger.info("Already on eligibility page, skipping navigation...")
                return
            
            # First request - manual navigation required
            logger.info("="*60)
            logger.info("MANUAL NAVIGATION REQUIRED")
            logger.info("="*60)
            logger.info("Please manually navigate to the Eligibility page NOW")
            logger.info("The bot will wait 15 seconds for you to navigate...")
            logger.info("="*60)
            
            import time
            time.sleep(15)
            
            logger.info(f"Current URL: {self.driver.current_url}")
            logger.info("Proceeding with form filling...")

        except Exception as e:
            logger.error(f"Navigation check failed: {e}")
            raise PortalChangedError(f"Eligibility page navigation failed: {e}") from e

    def is_on_eligibility_page(self) -> bool:
        """
        Check if currently on the eligibility page.

        Returns:
            True if on eligibility page, False otherwise
        """
        return self.exists(self.ELIGIBILITY_PAGE_MARKER, timeout=3)

