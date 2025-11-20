"""Eligibility bot with retry logic and error handling."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import settings
from core import PortalBusinessError, PortalChangedError, SessionManager, TransientError, ValidationError, create_driver
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
        driver: Optional[WebDriver] = None,
    ):
        """
        Initialize eligibility bot.

        Args:
            base_url: Availity portal base URL
            username: Portal username
            password: Portal password
            headless: Run browser in headless mode
            artifacts_dir: Directory for error screenshots/HTML
            driver: Optional shared WebDriver instance (if None, creates new one)
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.headless = headless
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.driver: Optional[WebDriver] = driver  # Use provided driver or None
        self._owns_driver = driver is None  # Track if we own the driver
        self.login_page: Optional[LoginPage] = None
        self.dashboard_page: Optional[DashboardPage] = None
        self.eligibility_page: Optional[EligibilityPage] = None

    def _init_driver(self) -> None:
        """Initialize WebDriver and page objects."""
        if self.driver is None:
            logger.info("Initializing Chrome WebDriver")
            self.driver = create_driver(headless=self.headless)
        
        # Initialize page objects if not already done
        if self.login_page is None:
            assert self.driver is not None
            self.login_page = LoginPage(self.driver)
            self.dashboard_page = DashboardPage(self.driver)
            self.eligibility_page = EligibilityPage(self.driver)

    def login(self) -> None:
        """
        Login to the Availity portal.
        
        First tries to load saved cookies. If cookies are invalid or don't exist,
        performs fresh login and saves cookies for next time.

        Raises:
            PortalChangedError: If login page structure changed
        """
        self._init_driver()
        assert self.driver is not None
        assert self.login_page is not None

        logger.info("Starting login process")

        # Initialize session manager
        session_mgr = SessionManager()

        # Try to load saved cookies first
        session_valid = False
        if session_mgr.cookies_exist():
            logger.info("Found saved cookies, attempting to load...")
            cookies_loaded = session_mgr.load_cookies(self.driver)
            
            if cookies_loaded:
                # Navigate directly to eligibility page URL (with cookies, skips login and dashboard)
                # This is faster than going through login page and dashboard
                eligibility_url = settings.ELIGIBILITY_URL
                logger.info(f"Navigating directly to eligibility page with saved cookies: {eligibility_url}")
                self.driver.get(eligibility_url)
                import time
                time.sleep(5)  # Give page time to load (eligibility page takes longer)
                
                # Check if we're logged in by checking current URL and page elements
                current_url = self.driver.current_url
                if 'login' in current_url.lower():
                    logger.warning("Redirected to login page - cookies expired or invalid")
                elif self.login_page.is_logged_in() or session_mgr.is_session_valid(self.driver):
                    logger.info("Session is valid! Using saved cookies - skipped login and dashboard, went directly to eligibility page.")
                    session_valid = True
                else:
                    logger.warning("Could not verify session - will perform fresh login")
        else:
            logger.info("No saved cookies found, will perform fresh login")

        # If no cookies or cookies invalid, perform login with autofill
        if not session_valid:
            # Navigate to login page
            logger.info("Navigating to login page for fresh login...")
            self.login_page.open(self.base_url)

            # Check if already logged in (edge case)
            if self.login_page.is_logged_in():
                logger.info("Already logged in")
                # Save cookies even if we didn't login (session might be valid)
                session_mgr.save_cookies(self.driver, metadata={"username": self.username})
                return

            # Perform login with autofill (username and password from config)
            logger.info(f"Performing fresh login for user: {self.username}")
            self.login_page.login(self.username, self.password, save_cookies=True)
            logger.info("Login completed successfully and cookies saved")

    @retry(
        retry=retry_if_exception_type(TransientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def process_request(self, request: EligibilityRequest, use_multiple_patients: bool = False, multiple_patients_data: Optional[list[dict]] = None) -> EligibilityResult:
        """
        Process a single eligibility request.

        Applies retry logic for transient errors. Does NOT retry for:
        - ValidationError: Bad input data
        - PortalChangedError: Portal structure changed (needs manual fix)
        - PortalBusinessError: Portal returned business error

        Args:
            request: EligibilityRequest to process
            use_multiple_patients: If True, use Multiple Patients tab instead of single patient form
            multiple_patients_data: List of patient dicts for multiple patients mode (if None and use_multiple_patients=True, uses request as single entry)

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

            # Initialize driver and page objects (needed for shared driver)
            self._init_driver()
            
            # Ensure we're logged in (check if session is valid, login if needed)
            assert self.driver is not None
            assert self.login_page is not None
            
            # Check if we need to login (for shared driver, check session validity)
            session_mgr = SessionManager()
            needs_login = True
            if session_mgr.cookies_exist():
                # Try to verify session without navigating
                try:
                    current_url = self.driver.current_url
                    if 'login' not in current_url.lower() and self.login_page.is_logged_in():
                        needs_login = False
                        logger.info("Already logged in with shared driver")
                except:
                    pass  # If check fails, we'll do login
            
            if needs_login:
                self.login()

            assert self.dashboard_page is not None
            assert self.eligibility_page is not None

            # Navigate to eligibility section (only if not already there)
            # If we used cookies, we might already be on eligibility page
            if not self.dashboard_page.is_on_eligibility_page():
                logger.info("Not on eligibility page, navigating...")
                self.dashboard_page.go_to_eligibility()
            else:
                logger.info("Already on eligibility page, skipping navigation")

            # Ensure eligibility form is loaded
            self.eligibility_page.ensure_loaded()

            # Fill and submit form
            self.eligibility_page.fill_request_form(request, use_multiple_patients=use_multiple_patients, multiple_patients_data=multiple_patients_data)
            self.eligibility_page.submit()

            # Wait for results - increased timeout to allow patient history crawling
            self.eligibility_page.wait_for_results(timeout=120)  # 2 minutes for results to fully load

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
        
        Saves both the wrapper page and iframe content if available.

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
            
            # Save main page HTML
            html_source = self.driver.page_source
            
            # Try to also get iframe content
            try:
                from selenium.webdriver.common.by import By
                self.driver.switch_to.default_content()
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    self.driver.switch_to.frame(iframes[0])
                    iframe_html = self.driver.page_source
                    # Combine both HTMLs with clear separation
                    html_source = f"<!-- WRAPPER PAGE -->\n{html_source}\n\n<!-- IFRAME CONTENT -->\n{iframe_html}"
                    self.driver.switch_to.default_content()
            except Exception as e:
                logger.debug(f"Could not capture iframe content: {e}")
            
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
        """Close the browser and clean up resources (only if we own the driver)."""
        if self.driver is not None and self._owns_driver:
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
        elif self.driver is not None:
            # Shared driver - just clear reference, don't close
            logger.debug("Skipping close for shared WebDriver")
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

