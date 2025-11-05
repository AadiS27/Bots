# Selector Update Guide

This guide shows you how to find and update the placeholder selectors with real ones from the Availity portal.

## Step 1: Inspect the Availity Portal

### A. Open the Portal in Chrome

1. Navigate to `https://apps.availity.com` in Chrome
2. Log in with your credentials manually
3. Navigate through the eligibility workflow

### B. Find Login Page Selectors

1. **Before logging in**, right-click on the username field → **Inspect**
2. In Chrome DevTools, look for attributes like:
   - `id="username"` or `id="userId"` or similar
   - `name="username"`
   - `data-testid="username-input"`
   - Or a unique CSS class

**Example:**
```html
<!-- If you see this: -->
<input id="availity-username" type="text" name="user" />

<!-- Update login_page.py with: -->
USERNAME_INPUT = (By.ID, "availity-username")
```

3. Repeat for:
   - **Password field**
   - **Login button**
   - **Dashboard marker** (any element that appears ONLY after login, like a menu or logout button)

### C. Find Dashboard/Navigation Selectors

After logging in:

1. Look for the **Eligibility** link/button
2. Right-click → Inspect
3. Note the selector (link text, CSS selector, etc.)

**Example:**
```html
<!-- If you see: -->
<a href="/payer-spaces/eligibility">Eligibility & Benefits</a>

<!-- Update dashboard_page.py with: -->
ELIGIBILITY_LINK = (By.LINK_TEXT, "Eligibility & Benefits")
```

### D. Find Eligibility Form Selectors

On the eligibility page:

1. Inspect each form field:
   - Payer dropdown
   - Member ID input
   - Last name input
   - First name input
   - Date of birth input
   - Date of service fields
   - Submit button

2. Inspect result elements:
   - Results container
   - Coverage status field
   - Plan name field
   - Deductible fields
   - Benefits table rows

## Step 2: Update the Page Objects

### File: `pages/login_page.py`

Find the lines with `# TODO:` and update:

```python
# Before (placeholder):
USERNAME_INPUT = (By.ID, "username")  # TODO: Replace with actual selector

# After (example - use your actual selector):
USERNAME_INPUT = (By.ID, "availity-username")
```

Update all 4 selectors:
1. `USERNAME_INPUT`
2. `PASSWORD_INPUT`
3. `LOGIN_BUTTON`
4. `DASHBOARD_MARKER`

### File: `pages/dashboard_page.py`

Update:
1. `ELIGIBILITY_MENU` (if there's a dropdown menu)
2. `ELIGIBILITY_LINK` (the actual link to click)
3. `ELIGIBILITY_PAGE_MARKER` (element that confirms you're on eligibility page)

### File: `pages/eligibility_page.py`

This is the most complex file. Update:

**Form Fields:**
1. `PAYER_DROPDOWN`
2. `MEMBER_ID_INPUT`
3. `LAST_NAME_INPUT`
4. `FIRST_NAME_INPUT`
5. `DOB_INPUT`
6. `DOS_FROM_INPUT`
7. `DOS_TO_INPUT`
8. `SERVICE_TYPE_DROPDOWN`
9. `PROVIDER_NPI_INPUT`
10. `SUBMIT_BUTTON`

**Results Fields:**
1. `RESULTS_CONTAINER`
2. `COVERAGE_STATUS`
3. `PLAN_NAME`
4. `PLAN_TYPE`
5. `COVERAGE_DATES`
6. `DEDUCTIBLE_INDIVIDUAL`
7. `DEDUCTIBLE_REMAINING`
8. `OOP_MAX_INDIVIDUAL`
9. `OOP_MAX_FAMILY`
10. `BENEFITS_TABLE`
11. `BENEFITS_ROWS`

## Step 3: Selector Types Reference

### By.ID (Best - most stable)
```python
(By.ID, "member-id")
```

### By.NAME
```python
(By.NAME, "memberId")
```

### By.CSS_SELECTOR (Very flexible)
```python
(By.CSS_SELECTOR, "input[name='memberID']")
(By.CSS_SELECTOR, ".form-control[placeholder='Member ID']")
(By.CSS_SELECTOR, "#eligibility-form input.member-input")
```

### By.XPATH (Powerful but brittle)
```python
(By.XPATH, "//input[@placeholder='Member ID']")
(By.XPATH, "//button[contains(text(), 'Submit')]")
```

### By.LINK_TEXT (For links)
```python
(By.LINK_TEXT, "Eligibility and Benefits")
```

### By.PARTIAL_LINK_TEXT
```python
(By.PARTIAL_LINK_TEXT, "Eligibility")
```

### By.CLASS_NAME (Single class only)
```python
(By.CLASS_NAME, "eligibility-results")
```

## Step 4: Tips for Finding Stable Selectors

### Prefer (in order):
1. **`id` attributes** - Most stable
2. **`data-testid` or `data-test` attributes** - Made for testing
3. **`name` attributes** - Usually stable
4. **Unique CSS classes** - Be careful, classes can change
5. **Combination selectors** - More specific = more stable

### Avoid:
- Generic classes like `.btn`, `.form-control`
- XPath with position indices like `[1]`, `[2]`
- Overly complex selectors

### Good Examples:
```python
# Good: Uses ID
USERNAME_INPUT = (By.ID, "userId")

# Good: Uses data attribute
SUBMIT_BTN = (By.CSS_SELECTOR, "[data-testid='submit-button']")

# Good: Specific combination
MEMBER_ID = (By.CSS_SELECTOR, "#eligibility-form input[name='memberId']")
```

### Bad Examples:
```python
# Bad: Too generic
BUTTON = (By.CLASS_NAME, "btn")

# Bad: Position-based (brittle)
FIRST_INPUT = (By.XPATH, "//input[1]")

# Bad: Too specific, will break with minor changes
BAD = (By.XPATH, "/html/body/div[1]/div[2]/form/div[3]/input[1]")
```

## Step 5: Testing Your Updates

After updating each file, test incrementally:

### Test Login Only:
```python
# Create a test script: test_login.py
from config import settings
from core import create_driver
from pages import LoginPage

driver = create_driver(headless=False)
try:
    login_page = LoginPage(driver)
    login_page.open(settings.BASE_URL)
    login_page.login(settings.USERNAME, settings.PASSWORD)
    print("Login successful!")
    input("Press Enter to close browser...")
finally:
    driver.quit()
```

### Test Full Flow:
```powershell
python scripts/run_eligibility.py --input sample/input_eligibility.json --output sample/output_test.json --no-headless
```

## Step 6: Common Issues

### Issue: Element not found
**Solution**: 
- Check if element is in an iframe: `switch_to_iframe()`
- Wait longer: increase `timeout` parameter
- Element might load dynamically: check network tab

### Issue: Element not clickable
**Solution**:
- Scroll to element first: `scroll_to_element()`
- Wait for clickable instead of visible: `wait_for_clickable()`
- Another element might be overlaying it

### Issue: Stale element reference
**Solution**:
- This is handled by retry logic
- Refind the element instead of storing it

## Step 7: Special Cases

### Dropdown/Select Elements

If using a standard `<select>` tag:
```python
from selenium.webdriver.support.ui import Select

dropdown = Select(self.wait_for_visible(self.PAYER_DROPDOWN))
dropdown.select_by_visible_text(payer_name)
```

### Autocomplete/Searchable Dropdowns

```python
# Click to open
self.click(self.PAYER_DROPDOWN)

# Type to search
self.type(self.PAYER_SEARCH, payer_name)

# Click first result
self.click((By.CSS_SELECTOR, ".autocomplete-item:first-child"))
```

### Date Pickers

Some date pickers require clicking to open, then selecting:
```python
# Open date picker
self.click(self.DOB_INPUT)

# Type date directly
self.type(self.DOB_INPUT, "06/15/1987", clear_first=False)

# Or interact with calendar widget
```

### iFrames

If form is in an iframe:
```python
# Switch to iframe
self.switch_to_iframe((By.ID, "eligibility-iframe"))

# Do your work
self.type(self.MEMBER_ID_INPUT, member_id)

# Switch back
self.switch_to_default_content()
```

## Step 8: Debugging Tips

### Enable Selenium Logging:
In `db/engine.py`, set `echo=True` to see SQL queries.

### Add Debug Sleeps (temporarily):
```python
import time
time.sleep(5)  # Pause to inspect browser state
```

### Take Screenshots:
```python
driver.save_screenshot("debug.png")
```

### Print Page Source:
```python
print(driver.page_source)
```

---

## Quick Reference Card

| What | Where | How |
|------|-------|-----|
| **Login selectors** | `pages/login_page.py` | Lines 16-19 |
| **Dashboard navigation** | `pages/dashboard_page.py` | Lines 16-18 |
| **Form fields** | `pages/eligibility_page.py` | Lines 21-31 |
| **Results parsing** | `pages/eligibility_page.py` | Lines 34-46 |
| **Test incrementally** | Create `test_login.py` | Test each page separately |

---

**Remember**: Start with login page, test it works, then move to dashboard, then eligibility form. Don't try to do everything at once!

