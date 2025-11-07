"""
Session/Cookie manager for Availity RPA.
Saves and loads cookies to avoid repeated logins.
"""
import json
from pathlib import Path
from typing import Optional, Dict
from selenium.webdriver.remote.webdriver import WebDriver
from datetime import datetime
from loguru import logger


class SessionManager:
    """Manages browser session cookies for persistent login"""
    
    def __init__(self, cookies_file: str = "availity_session_cookies.json"):
        """
        Initialize session manager.
        
        Args:
            cookies_file: Path to file where cookies are stored
        """
        self.cookies_file = Path(cookies_file)
        self.session_dir = self.cookies_file.parent
        self.session_dir.mkdir(exist_ok=True)
    
    def save_cookies(self, driver: WebDriver, metadata: Optional[Dict] = None):
        """
        Save current browser cookies to file.
        
        Args:
            driver: WebDriver instance
            metadata: Optional metadata to save (e.g., expiry time, username)
        """
        # Get all cookies from the browser
        cookies = driver.get_cookies()
        
        if not cookies:
            logger.warning("No cookies found in browser to save!")
            logger.debug(f"Current URL: {driver.current_url}")
            return
        
        logger.info(f"Found {len(cookies)} cookies to save")
        
        session_data = {
            "cookies": cookies,
            "saved_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        with open(self.cookies_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2)
        
        logger.info(f"Cookies saved to: {self.cookies_file}")
        cookie_names = ', '.join([c.get('name', 'unknown') for c in cookies[:5]])
        logger.debug(f"Cookie names: {cookie_names}")
    
    def load_cookies(self, driver: WebDriver) -> bool:
        """
        Load cookies from file and add to browser.
        
        Args:
            driver: WebDriver instance
        
        Returns:
            True if cookies were loaded successfully, False otherwise
        """
        if not self.cookies_file.exists():
            logger.info("No saved cookies found")
            return False
        
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            cookies = session_data.get("cookies", [])
            if not cookies:
                logger.warning("Cookie file exists but is empty")
                return False
            
            # Navigate to domain first (required for adding cookies)
            # Use the base URL to ensure cookies can be added
            base_url = "https://apps.availity.com"
            logger.info(f"Navigating to {base_url} to load cookies...")
            driver.get(base_url)
            
            # Wait a moment for page to load
            import time
            time.sleep(2)
            
            # Add each cookie
            added_count = 0
            skipped_count = 0
            for cookie in cookies:
                try:
                    # Remove 'expiry' if it's in the past (some browsers don't like expired cookies)
                    if 'expiry' in cookie:
                        expiry_time = datetime.fromtimestamp(cookie['expiry'])
                        if expiry_time < datetime.now():
                            skipped_count += 1
                            continue
                    
                    # Remove 'sameSite' if it's 'None' (Selenium doesn't accept 'None' as string)
                    cookie_copy = cookie.copy()
                    if cookie_copy.get('sameSite') == 'None':
                        cookie_copy['sameSite'] = 'Lax'
                    
                    driver.add_cookie(cookie_copy)
                    added_count += 1
                except Exception as e:
                    skipped_count += 1
                    logger.warning(f"Could not add cookie {cookie.get('name')}: {e}")
            
            saved_at = session_data.get("saved_at", "unknown")
            logger.info(f"Loaded {added_count} cookies (skipped {skipped_count} expired/invalid, saved at: {saved_at})")
            return added_count > 0
        
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False
    
    def cookies_exist(self) -> bool:
        """Check if cookie file exists"""
        return self.cookies_file.exists()
    
    def delete_cookies(self):
        """Delete saved cookies file"""
        if self.cookies_file.exists():
            self.cookies_file.unlink()
            logger.info(f"Deleted cookies file: {self.cookies_file}")
    
    def is_session_valid(self, driver: WebDriver) -> bool:
        """
        Check if current session is valid by checking URL and page elements.
        
        Args:
            driver: WebDriver instance
        
        Returns:
            True if session appears valid
        """
        try:
            from selenium.webdriver.common.by import By
            import time
            
            current_url = driver.current_url
            logger.debug(f"Checking session validity... URL: {current_url}")
            
            # First check: If we're on login page, definitely not logged in
            if 'login' in current_url.lower():
                logger.debug("On login page - session invalid")
                return False
            
            # Second check: If we're on apps.availity.com but NOT login, likely logged in
            if 'apps.availity.com' in current_url and 'login' not in current_url.lower():
                # Check if login input field exists (means we're on login page despite URL)
                login_input = driver.find_elements(By.ID, "userId")
                if login_input:
                    logger.debug("Login input found - session invalid")
                    return False
                
                # Wait a moment for page to load, then check for any dashboard indicators
                time.sleep(2)
                
                # Try to find dashboard marker (account button appears after login)
                try:
                    dashboard_marker = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Account']")
                    if dashboard_marker:
                        logger.debug("Dashboard marker found - session valid")
                        return True
                except:
                    pass
                
                # If page title is not "login" or "sign in", likely valid
                page_title = driver.title.lower()
                if 'login' not in page_title and 'sign in' not in page_title:
                    logger.debug("Page title indicates logged in - session valid")
                    return True
            
            # Default: if we got here and not on login page, assume valid
            logger.debug("Session appears valid (not on login page)")
            return True
            
        except Exception as e:
            # If there's an error checking, be conservative and assume invalid
            logger.warning(f"Session validation error: {e}")
            return False
    
    def get_session_info(self) -> Optional[Dict]:
        """Get information about saved session"""
        if not self.cookies_file.exists():
            return None
        
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            return session_data
        except:
            return None

