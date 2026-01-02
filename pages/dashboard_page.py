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

    def go_to_eligibility(self) -> None:
        """
        Navigate to the Eligibility section.
        
        NOTE: Currently assumes user manually navigates to eligibility page.
        Navigation will be fixed later.

        Raises:
            PortalChangedError: If navigation fails
        """
        try:
            logger.info("="*60)
            logger.info("MANUAL NAVIGATION REQUIRED")
            logger.info("="*60)
            logger.info("Please manually navigate to the Eligibility page NOW")
            logger.info("The bot will wait 30 seconds for you to navigate...")
            logger.info("="*60)
            
            import time
            time.sleep(30)  # Give user 30 seconds to manually navigate
            
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

    def go_to_claim_status(self) -> None:
        """
        Navigate to the Claim Status section.
        
        NOTE: Currently assumes user manually navigates to claim status page.
        Navigation will be fixed later.

        Raises:
            PortalChangedError: If navigation fails
        """
        try:
            logger.info("="*60)
            logger.info("MANUAL NAVIGATION REQUIRED")
            logger.info("="*60)
            logger.info("Please manually navigate to the Claim Status page NOW")
            logger.info("The bot will wait 30 seconds for you to navigate...")
            logger.info("="*60)
            
            import time
            time.sleep(30)  # Give user 30 seconds to manually navigate
            
            logger.info(f"Current URL: {self.driver.current_url}")
            logger.info("Proceeding with form filling...")

        except Exception as e:
            logger.error(f"Navigation check failed: {e}")
            raise PortalChangedError(f"Claim Status page navigation failed: {e}") from e

    def is_on_claim_status_page(self) -> bool:
        """
        Check if currently on the claim status page.

        Returns:
            True if on claim status page, False otherwise
        """
        # TODO: Add proper marker for claim status page
        # For now, check for form elements similar to eligibility
        return self.exists(self.ELIGIBILITY_PAGE_MARKER, timeout=3)  # Reuse for now

    def go_to_appeals(self) -> None:
        """
        Navigate to the Appeals section.
        
        NOTE: Currently assumes user manually navigates to appeals page.
        Navigation will be fixed later.

        Raises:
            PortalChangedError: If navigation fails
        """
        try:
            logger.info("="*60)
            logger.info("MANUAL NAVIGATION REQUIRED")
            logger.info("="*60)
            logger.info("Please manually navigate to the Appeals page NOW")
            logger.info("The bot will wait 30 seconds for you to navigate...")
            logger.info("="*60)
            
            import time
            time.sleep(30)  # Give user 30 seconds to manually navigate
            
            logger.info(f"Current URL: {self.driver.current_url}")
            logger.info("Proceeding with form filling...")

        except Exception as e:
            logger.error(f"Navigation check failed: {e}")
            raise PortalChangedError(f"Appeals page navigation failed: {e}") from e

    def is_on_appeals_page(self) -> bool:
        """
        Check if currently on the appeals page.

        Returns:
            True if on appeals page, False otherwise
        """
        # TODO: Add proper marker for appeals page
        # For now, check for form elements similar to eligibility
        return self.exists(self.ELIGIBILITY_PAGE_MARKER, timeout=3)  # Reuse for now

    def go_to_claims(self) -> None:
        """
        Navigate to the Claims submission section.
        
        NOTE: Currently assumes user manually navigates to claims page.
        Navigation will be fixed later.

        Raises:
            PortalChangedError: If navigation fails
        """
        try:
            logger.info("="*60)
            logger.info("MANUAL NAVIGATION REQUIRED")
            logger.info("="*60)
            logger.info("Please manually navigate to the Claims submission page NOW")
            logger.info("The bot will wait 30 seconds for you to navigate...")
            logger.info("="*60)
            
            import time
            time.sleep(30)  # Give user 30 seconds to manually navigate
            
            logger.info(f"Current URL: {self.driver.current_url}")
            logger.info("Proceeding with form filling...")

        except Exception as e:
            logger.error(f"Navigation check failed: {e}")
            raise PortalChangedError(f"Claims page navigation failed: {e}") from e

    def is_on_claims_page(self) -> bool:
        """
        Check if currently on the claims submission page.

        Returns:
            True if on claims page, False otherwise
        """
        # TODO: Add proper marker for claims page
        # For now, check for form elements similar to eligibility
        return self.exists(self.ELIGIBILITY_PAGE_MARKER, timeout=3)  # Reuse for now


    def go_to_drug_prior_auth(self) -> None:
        """
        Navigate to the Drug Prior Authorization section.
        
        NOTE: Currently assumes user manually navigates to drug prior auth page.
        Navigation will be fixed later.

        Raises:
            PortalChangedError: If navigation fails
        """
        try:
            logger.info("="*60)
            logger.info("MANUAL NAVIGATION REQUIRED")
            logger.info("="*60)
            logger.info("Please manually navigate to the Drug Prior Authorization page NOW")
            logger.info("The bot will wait 30 seconds for you to navigate...")
            logger.info("="*60)
            
            import time
            time.sleep(30)  # Give user 30 seconds to manually navigate
            
            logger.info(f"Current URL: {self.driver.current_url}")
            logger.info("Proceeding with form filling...")

        except Exception as e:
            logger.error(f"Navigation check failed: {e}")
            raise PortalChangedError(f"Drug Prior Authorization page navigation failed: {e}") from e

    def is_on_drug_prior_auth_page(self) -> bool:
        """
        Check if currently on the drug prior auth page.

        Returns:
            True if on drug prior auth page, False otherwise
        """
        # Check for Select2 containers
        return self.exists(
            (By.CSS_SELECTOR, "span.select2-chosen"), timeout=3
        )