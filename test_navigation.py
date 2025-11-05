"""
Test script to verify login and navigation to eligibility page.
Browser stays open so you can inspect what page we're on.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from core import create_driver, setup_logging
from pages import LoginPage, DashboardPage

setup_logging(log_level="INFO")


def test_navigation():
    """Test login and navigation, keep browser open."""
    print("\n" + "="*60)
    print("TESTING LOGIN + NAVIGATION")
    print("="*60 + "\n")
    
    driver = create_driver(headless=False)
    
    try:
        # Step 1: Login
        print("Step 1: Logging in...")
        login_page = LoginPage(driver)
        login_page.open(settings.BASE_URL)
        
        input("Browser opened. Press Enter when ready to login (or Ctrl+C to stop)...")
        
        login_page.login(settings.USERNAME, settings.PASSWORD)
        print("✓ Login successful!\n")
        
        input("Press Enter to navigate to eligibility page...")
        
        # Step 2: Navigate to eligibility
        print("\nStep 2: Navigating to eligibility page...")
        dashboard_page = DashboardPage(driver)
        dashboard_page.go_to_eligibility()
        print("✓ Navigation complete!\n")
        
        # Show current URL
        print("="*60)
        print(f"Current URL: {driver.current_url}")
        print("="*60)
        
        print("\nBrowser will stay open.")
        print("Look at the page - are you on the eligibility form?")
        print("\nIf YES:")
        print("  1. Right-click on any input field → Inspect")
        print("  2. Share the HTML with me")
        print("\nIf NO:")
        print("  1. Tell me what page you're on")
        print("  2. Manually navigate to eligibility")
        print("  3. Share the final URL")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}")
        print(f"Message: {e}\n")
        print(f"Current URL: {driver.current_url}")
        input("\nPress Enter to close browser...")
        return False
        
    finally:
        driver.quit()
    
    return True


if __name__ == "__main__":
    test_navigation()

