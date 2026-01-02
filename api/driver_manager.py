"""Shared WebDriver manager for API server."""

import threading
from typing import Optional
from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver

from core import create_driver


class WebDriverManager:
    """Manages a shared WebDriver instance across API requests."""
    
    _instance: Optional['WebDriverManager'] = None
    _instance_lock = threading.Lock()
    
    def __init__(self):
        """Initialize the WebDriver manager."""
        self.driver: Optional[WebDriver] = None
        self.headless: bool = False
        self._initialized: bool = False
        self._driver_lock = threading.Lock()  # Lock for driver creation/access
        self._usage_lock = threading.Lock()  # Lock to ensure only one request uses driver at a time
    
    @classmethod
    def get_instance(cls) -> 'WebDriverManager':
        """Get singleton instance of WebDriverManager."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_driver(self, headless: bool = False) -> WebDriver:
        """
        Get or create the shared WebDriver instance.
        
        This method is thread-safe and ensures only one driver instance exists.
        However, callers should use acquire_driver() and release_driver() to ensure
        exclusive access during bot operations.
        
        Args:
            headless: Whether to run in headless mode (only used on first creation)
            
        Returns:
            The shared WebDriver instance
        """
        with self._driver_lock:
            if self.driver is None:
                logger.info("Creating shared WebDriver instance")
                self.headless = headless
                self.driver = create_driver(headless=headless)
                self._initialized = True
                logger.info("Shared WebDriver created successfully")
            elif not self._is_driver_alive():
                logger.warning("WebDriver session expired, recreating...")
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = create_driver(headless=self.headless)
                logger.info("WebDriver recreated successfully")
            
            return self.driver
    
    def acquire_driver(self, headless: bool = False) -> WebDriver:
        """
        Acquire exclusive access to the shared WebDriver.
        
        This method blocks until the driver is available, ensuring only one
        request uses it at a time. Callers MUST call release_driver() when done.
        
        Args:
            headless: Whether to run in headless mode (only used on first creation)
            
        Returns:
            The shared WebDriver instance
        """
        self._usage_lock.acquire()
        logger.debug("Acquired exclusive access to shared WebDriver")
        return self.get_driver(headless=headless)
    
    def release_driver(self) -> None:
        """
        Release exclusive access to the shared WebDriver.
        
        This must be called after acquire_driver() to allow other requests to proceed.
        """
        logger.debug("Releasing exclusive access to shared WebDriver")
        self._usage_lock.release()
    
    def _is_driver_alive(self) -> bool:
        """Check if the current driver session is still alive."""
        if self.driver is None:
            return False
        try:
            # Try to get current URL to check if session is alive
            _ = self.driver.current_url
            return True
        except Exception as e:
            logger.debug(f"Driver session check failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the shared WebDriver instance."""
        with self._lock:
            if self.driver is not None:
                logger.info("Closing shared WebDriver")
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.warning(f"Error closing shared driver: {e}")
                finally:
                    self.driver = None
                    self._initialized = False
                    logger.info("Shared WebDriver closed")
    
    def reset(self) -> None:
        """Reset the driver (close and clear)."""
        self.close()

