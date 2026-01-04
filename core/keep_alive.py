"""Keep-alive service to prevent Availity portal session timeout."""

import threading
import time
from typing import Optional
from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver

from config import settings
from core.session_manager import SessionManager
from pages.login_page import LoginPage


class KeepAliveService:
    """
    Background service to keep Availity portal session alive.
    
    Runs a keep-alive action every 10-12 minutes to prevent session timeout.
    Uses the same WebDriver instance as bot operations, so activity from this
    thread keeps the session alive for ALL threads using that driver.
    """

    def __init__(self, driver_manager, interval_minutes: int = 12):
        """
        Initialize keep-alive service.

        Args:
            driver_manager: WebDriverManager instance (for thread-safe driver access)
            interval_minutes: Interval between keep-alive actions in minutes (default: 12)
        """
        self.driver_manager = driver_manager
        self.interval_seconds = interval_minutes * 60
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    def start(self) -> None:
        """Start the keep-alive service in a background thread."""
        if self._running:
            logger.warning("Keep-alive service is already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="KeepAliveService")
        self._thread.start()
        self._running = True
        logger.info(f"Keep-alive service started (interval: {self.interval_seconds // 60} minutes)")

    def stop(self) -> None:
        """Stop the keep-alive service."""
        if not self._running:
            return

        logger.info("Stopping keep-alive service...")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._running = False
        logger.info("Keep-alive service stopped")

    def _run(self) -> None:
        """Main loop for keep-alive service."""
        logger.info("Keep-alive service thread started")
        
        while not self._stop_event.is_set():
            try:
                # Wait for interval or until stop event
                if self._stop_event.wait(timeout=self.interval_seconds):
                    # Stop event was set, exit loop
                    break

                # Perform keep-alive action
                self._perform_keep_alive()

            except Exception as e:
                logger.error(f"Error in keep-alive service: {e}")
                # Continue running even if there's an error
                time.sleep(60)  # Wait 1 minute before retrying

        logger.info("Keep-alive service thread stopped")

    def _perform_keep_alive(self) -> None:
        """
        Perform keep-alive action to prevent session timeout.
        
        Uses the same locking mechanism as bot operations to ensure thread safety.
        The activity in the shared browser session keeps ALL threads' sessions alive.
        """
        driver: Optional[WebDriver] = None
        try:
            logger.info("Performing keep-alive action...")
            
            # Acquire driver using the same locking mechanism as bot operations
            # This ensures thread safety and prevents conflicts with active bot operations
            driver = self.driver_manager.acquire_driver()
            
            if driver is None:
                logger.warning("No driver available for keep-alive - driver may not be initialized yet")
                return

            # Check if session is still valid
            session_mgr = SessionManager()
            is_valid = self._check_session_validity(driver, session_mgr)

            if is_valid:
                # Session is valid - perform lightweight keep-alive action
                # This activity in the shared browser keeps the session alive for ALL threads
                self._keep_session_alive(driver)
            else:
                # Session expired - attempt to re-login
                logger.warning("Session expired during keep-alive - attempting to re-login...")
                self._re_login(driver, session_mgr)

            logger.info("Keep-alive action completed successfully")

        except Exception as e:
            logger.error(f"Error during keep-alive action: {e}")
            # Don't raise - we want the service to continue running
        finally:
            # Always release the driver lock (same as bot operations)
            if driver is not None:
                try:
                    self.driver_manager.release_driver()
                    logger.debug("Keep-alive: Released driver lock")
                except Exception as e:
                    logger.warning(f"Error releasing driver lock: {e}")

    def _check_session_validity(self, driver: WebDriver, session_mgr: SessionManager) -> bool:
        """
        Check if the current session is still valid.

        Args:
            driver: WebDriver instance
            session_mgr: SessionManager instance

        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Quick check: try to get current URL
            current_url = driver.current_url
            
            # If we're on login page, session is invalid
            if 'login' in current_url.lower():
                logger.debug("Keep-alive: On login page - session invalid")
                return False

            # Use session manager's validation
            is_valid = session_mgr.is_session_valid(driver)
            logger.debug(f"Keep-alive: Session validity check: {is_valid}")
            return is_valid

        except Exception as e:
            logger.warning(f"Keep-alive: Error checking session validity: {e}")
            # If we can't check, assume invalid to be safe
            return False

    def _keep_session_alive(self, driver: WebDriver) -> None:
        """
        Perform a lightweight action to keep the session alive.
        
        This activity in the shared browser session keeps ALL threads' sessions alive,
        because Availity tracks activity at the browser/session level, not per thread.

        Args:
            driver: WebDriver instance
        """
        try:
            # Navigate to dashboard (lightweight, keeps session active)
            # This activity resets Availity's inactivity timer for the entire session
            dashboard_url = settings.DASHBOARD_URL
            logger.debug(f"Keep-alive: Navigating to dashboard: {dashboard_url}")
            driver.get(dashboard_url)
            time.sleep(2)  # Brief wait for page to load

            logger.debug("Keep-alive: Session kept alive successfully")

        except Exception as e:
            logger.warning(f"Keep-alive: Error keeping session alive: {e}")
            raise

    def _re_login(self, driver: WebDriver, session_mgr: SessionManager) -> None:
        """
        Re-login to the portal when session expires.
        
        This re-establishes the session for ALL threads using the shared driver.

        Args:
            driver: WebDriver instance
            session_mgr: SessionManager instance
        """
        try:
            logger.info("Keep-alive: Attempting to re-login...")

            # Navigate to login page
            login_page = LoginPage(driver)
            login_page.open(settings.BASE_URL)

            # Perform login
            login_page.login(
                username=settings.USERNAME,
                password=settings.PASSWORD,
                save_cookies=True
            )

            logger.info("Keep-alive: Re-login successful - session restored for all threads")

        except Exception as e:
            logger.error(f"Keep-alive: Re-login failed: {e}")
            raise

    def is_running(self) -> bool:
        """Check if the keep-alive service is running."""
        return self._running