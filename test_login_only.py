"""
Simple script to test login page selectors only.

Use this to incrementally test your selector updates without running the full workflow.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from core import create_driver, setup_logging
from pages import LoginPage

setup_logging(log_level="INFO")


def test_login():
    """Test login functionality with current selectors."""
    print("\n" + "="*60)
    print("TESTING LOGIN PAGE SELECTORS")
    print("="*60 + "\n")
    
    print(f"Portal URL: {settings.BASE_URL}")
    print(f"Username: {settings.USERNAME}")
    print(f"Headless: False (browser will be visible)\n")
    
    driver = create_driver(headless=False)
    
    try:
        login_page = LoginPage(driver)
        
        print("Step 1: Opening portal...")
        login_page.open(settings.BASE_URL)
        print("SUCCESS: Portal opened\n")
        
        input("Press Enter to attempt login (or Ctrl+C to stop)...")
        
        print("\nStep 2: Attempting login...")
        login_page.login(settings.USERNAME, settings.PASSWORD, save_cookies=True)
        print("SUCCESS: Login completed!\n")
        print("✓ Cookies have been saved for future use")
        
        print("="*60)
        print("LOGIN TEST PASSED!")
        print("="*60)
        print("\nNext steps:")
        print("1. Browser will stay open for inspection")
        print("2. Press Enter to close browser and exit")
        print("3. If login succeeded, update dashboard_page.py selectors next")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}")
        print(f"Error: {e}\n")
        print("="*60)
        print("TROUBLESHOOTING:")
        print("="*60)
        print("1. Look at the browser - what's on screen?")
        print("2. Check if selectors match the actual page")
        print("3. Update selectors in pages/login_page.py")
        print("4. See SELECTOR_UPDATE_GUIDE.md for detailed help")
        
        input("\nPress Enter to close browser...")
        return False
        
    finally:
        driver.quit()
    
    return True


if __name__ == "__main__":
    success = test_login()
    sys.exit(0 if success else 1)

