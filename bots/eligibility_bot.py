"""Eligibility bot with retry logic and error handling."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core import PortalBusinessError, PortalChangedError, TransientError, ValidationError, create_driver
from domain import EligibilityRequest, EligibilityResult
from pages import DashboardPage, EligibilityPage, LoginPage


class EligibilityBot:
    """
    Bot for automated eligibility checking through Availity portal.

    Handles login, form filling, result parsing, and error recovery.
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        headless: bool = True,
        artifacts_dir: str = "artifacts",
    ):
        """
        Initialize eligibility bot.

        Args:
            base_url: Availity portal base URL
            username: Portal username
            password: Portal password
            headless: Run browser in headless mode
            artifacts_dir: Directory for error screenshots/HTML
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.headless = headless
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.driver: Optional[WebDriver] = None
        self.login_page: Optional[LoginPage] = None
        self.dashboard_page: Optional[DashboardPage] = None
        self.eligibility_page: Optional[EligibilityPage] = None

    def _init_driver(self) -> None:
        """Initialize WebDriver and page objects."""
        if self.driver is None:
            logger.info("Initializing Chrome WebDriver")
            self.driver = create_driver(headless=self.headless)
            self.login_page = LoginPage(self.driver)
            self.dashboard_page = DashboardPage(self.driver)
            self.eligibility_page = EligibilityPage(self.driver)

    def login(self) -> None:
        """
        Login to the Availity portal.

        Raises:
            PortalChangedError: If login page structure changed
        """
        self._init_driver()
        assert self.driver is not None
        assert self.login_page is not None

        logger.info("Starting login process")

        # Navigate to login page
        self.login_page.open(self.base_url)

        # Check if already logged in
        if self.login_page.is_logged_in():
            logger.info("Already logged in")
            return

        # Perform login
        self.login_page.login(self.username, self.password)
        logger.info("Login completed successfully")

    @retry(
        retry=retry_if_exception_type(TransientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def process_request(self, request: EligibilityRequest) -> EligibilityResult:
        """
        Process a single eligibility request.

        Applies retry logic for transient errors. Does NOT retry for:
        - ValidationError: Bad input data
        - PortalChangedError: Portal structure changed (needs manual fix)
        - PortalBusinessError: Portal returned business error

        Args:
            request: EligibilityRequest to process

        Returns:
            EligibilityResult with parsed data

        Raises:
            ValidationError: Invalid request data
            PortalChangedError: Portal structure changed
            PortalBusinessError: Portal returned business error
            TransientError: Recoverable error (will be retried)
        """
        try:
            logger.info(f"Processing eligibility request ID: {request.request_id}")

            # Ensure we're logged in
            if self.driver is None:
                self.login()

            assert self.dashboard_page is not None
            assert self.eligibility_page is not None

            # Navigate to eligibility section
            # For subsequent requests, skip manual navigation if already on eligibility page
            try:
                # Switch to default content first
                self.driver.switch_to.default_content()
                
                # Check if we're already on eligibility page (results page or form page)
                is_on_eligibility_page = False
                try:
                    # Check in default content first
                    if self.eligibility_page.exists(self.eligibility_page.RESULTS_CONTAINER, timeout=1) or \
                       self.eligibility_page.exists(self.eligibility_page.ERROR_MESSAGE, timeout=1):
                        is_on_eligibility_page = True
                        logger.info("Detected results page in default content - will reset form")
                    # Check if we're on the form page (in iframe)
                    else:
                        # Switch to iframe to check
                        from selenium.webdriver.common.by import By
                        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                        if iframes:
                            try:
                                self.driver.switch_to.frame(iframes[0])
                                if self.eligibility_page.exists(self.eligibility_page.PAYER_DROPDOWN, timeout=1):
                                    is_on_eligibility_page = True
                                    logger.info("Already on eligibility form page (in iframe)")
                                elif self.eligibility_page.exists(self.eligibility_page.RESULTS_CONTAINER, timeout=1) or \
                                     self.eligibility_page.exists(self.eligibility_page.ERROR_MESSAGE, timeout=1):
                                    is_on_eligibility_page = True
                                    logger.info("Detected results page in iframe - will reset form")
                                self.driver.switch_to.default_content()
                            except:
                                self.driver.switch_to.default_content()
                except Exception as e:
                    logger.debug(f"Error checking page state: {e}")
                
                if is_on_eligibility_page:
                    # Subsequent request - skip manual navigation, just reset form
                    logger.info("Subsequent request detected - resetting form and reloading...")
                    self.eligibility_page.reset_form()
                    # Wait longer for form to reset/reload (React app needs time)
                    import time
                    time.sleep(5)  # Increased wait time for form reset
                else:
                    # First request - need manual navigation
                    logger.info("First request - manual navigation required")
                    self.dashboard_page.go_to_eligibility(skip_manual=False)
                    
            except Exception as e:
                logger.debug(f"Navigation check failed: {e}, doing normal navigation...")
                self.dashboard_page.go_to_eligibility(skip_manual=False)

            # Ensure eligibility form is loaded (this will handle iframe switching)
            self.eligibility_page.ensure_loaded()

            # Fill and submit form
            self.eligibility_page.fill_request_form(request)
            self.eligibility_page.submit()

            # Wait for results
            self.eligibility_page.wait_for_results(timeout=30)

            # Parse result
            result = self.eligibility_page.parse_result(request)

            # Save raw HTML response
            html_path = self._save_response_html(request)
            result.raw_response_html_path = str(html_path) if html_path else None

            logger.info(f"Successfully processed request ID: {request.request_id}")
            return result

        except (ValidationError, PortalChangedError, PortalBusinessError):
            # Don't retry these - they need manual intervention or are permanent failures
            raise

        except Exception as e:
            # Treat unknown errors as transient (will be retried)
            logger.warning(f"Transient error processing request: {e}")
            raise TransientError(f"Transient error: {e}") from e

    def _save_response_html(self, request: EligibilityRequest) -> Optional[Path]:
        """
        Save the current page HTML as response artifact.

        Args:
            request: Request being processed

        Returns:
            Path to saved HTML file or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"response_{request.request_id}_{timestamp}.html"
            filepath = self.artifacts_dir / filename

            assert self.driver is not None
            html_source = self.driver.page_source
            filepath.write_text(html_source, encoding="utf-8")

            logger.debug(f"Saved response HTML: {filepath}")
            return filepath

        except Exception as e:
            logger.warning(f"Failed to save response HTML: {e}")
            return None

    def _capture_error_artifacts(self, request: EligibilityRequest, exc: Exception) -> None:
        """
        Capture screenshot and HTML on error.

        Args:
            request: Request being processed when error occurred
            exc: Exception that occurred
        """
        try:
            if self.driver is None:
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"error_{request.request_id}_{timestamp}"

            # Save screenshot
            screenshot_path = self.artifacts_dir / f"{base_filename}.png"
            self.driver.save_screenshot(str(screenshot_path))
            logger.info(f"Saved error screenshot: {screenshot_path}")

            # Save HTML
            html_path = self.artifacts_dir / f"{base_filename}.html"
            html_path.write_text(self.driver.page_source, encoding="utf-8")
            logger.info(f"Saved error HTML: {html_path}")

        except Exception as e:
            logger.warning(f"Failed to capture error artifacts: {e}")

    def close(self) -> None:
        """Close the browser and clean up resources."""
        if self.driver is not None:
            logger.info("Closing WebDriver")
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None
                self.login_page = None
                self.dashboard_page = None
                self.eligibility_page = None

    def __enter__(self) -> "EligibilityBot":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensure cleanup."""
        self.close()

