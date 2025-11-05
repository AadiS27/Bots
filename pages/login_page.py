"""Login page object for Availity portal."""

from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from core.errors import PortalChangedError

from .base_page import BasePage


class LoginPage(BasePage):
    """Page object for Availity login page."""

    # Actual Availity portal selectors
    USERNAME_INPUT = (By.ID, "userId")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    DASHBOARD_MARKER = (By.CSS_SELECTOR, "button[aria-label*='Account']")  # User account button appears after login

    def __init__(self, driver: WebDriver):
        """
        Initialize login page.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def open(self, url: str) -> None:
        """
        Navigate to the login page.

        Args:
            url: Base URL of the Availity portal
        """
        logger.info(f"Opening login page: {url}")
        self.driver.get(url)

    def login(self, username: str, password: str) -> None:
        """
        Perform login with provided credentials.
        
        Note: If 2FA is enabled, you have 2 minutes to manually enter the code.

        Args:
            username: Username/email
            password: Password

        Raises:
            PortalChangedError: If login elements not found (portal changed)
        """
        try:
            logger.info(f"Logging in as: {username}")

            # Wait for and fill username
            self.type(self.USERNAME_INPUT, username, timeout=15)

            # Fill password
            self.type(self.PASSWORD_INPUT, password, timeout=5)

            # Click login button
            self.click(self.LOGIN_BUTTON, timeout=5)

            # Wait for successful login (dashboard marker appears)
            # Extended timeout for 2FA: User has 2 minutes to enter code manually
            logger.info("Waiting for login to complete (if 2FA appears, enter code manually)...")
            self.wait_for_visible(self.DASHBOARD_MARKER, timeout=120)

            logger.info("Login successful")

        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise PortalChangedError(f"Login page structure may have changed: {e}") from e

    def is_logged_in(self) -> bool:
        """
        Check if user is already logged in.

        Returns:
            True if logged in, False otherwise
        """
        return self.exists(self.DASHBOARD_MARKER, timeout=3)

