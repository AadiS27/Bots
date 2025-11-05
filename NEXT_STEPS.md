# Next Steps - Make Your Bot Production Ready

## ✅ What's Working Now

- ✅ PostgreSQL database with all tables created
- ✅ Sample data enqueued (Request ID: 2 in database)
- ✅ Chrome WebDriver launches successfully
- ✅ Portal navigation starts correctly
- ✅ Error handling and logging works
- ✅ Console encoding fixed for Windows

## 🎯 What You Need to Do

### Step 1: Update Login Page Selectors (15-30 minutes)

**Goal**: Make the bot successfully log into Availity portal

1. **Open Chrome and manually log in to Availity**
   - Go to `https://apps.availity.com`
   - Note what you see on the login page

2. **Find the username input selector**
   - Right-click on username field → **Inspect**
   - Look for `id="..."` or `name="..."` in the highlighted code
   - Example: `<input id="userId" name="username" type="text">`

3. **Update `pages/login_page.py`**
   - Open the file in your editor
   - Find line ~16: `USERNAME_INPUT = (By.ID, "username")  # TODO`
   - Replace with actual selector, e.g., `USERNAME_INPUT = (By.ID, "userId")`

4. **Repeat for other login elements**:
   - `PASSWORD_INPUT` - The password field
   - `LOGIN_BUTTON` - The submit/login button
   - `DASHBOARD_MARKER` - Any element that appears ONLY after successful login (like a logout button or menu)

5. **Test login only**:
```powershell
cd E:\QuickIntell11\bots
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="E:\QuickIntell11\bots"
python test_login_only.py
```

**Expected result**: Browser opens, logs in successfully, and waits for you to press Enter.

---

### Step 2: Update Dashboard Navigation Selectors (10-15 minutes)

**Goal**: Navigate from dashboard to eligibility section

1. **After successful login, look for Eligibility link**
   - It might say "Eligibility", "Eligibility & Benefits", "Payer Spaces", etc.
   - Right-click → Inspect

2. **Update `pages/dashboard_page.py`**
   - Lines 16-18 have placeholder selectors
   - Update with actual link text or CSS selector
   - Example: `ELIGIBILITY_LINK = (By.LINK_TEXT, "Eligibility & Benefits")`

3. **Test**:
```powershell
python scripts/run_eligibility.py --input sample/input_eligibility.json --output sample/output_test.json --no-headless
```

**Expected result**: Browser logs in AND navigates to eligibility page.

---

### Step 3: Update Eligibility Form Selectors (30-60 minutes)

**Goal**: Fill and submit the eligibility check form

1. **Inspect the eligibility form**
   - Find each input field (payer, member ID, name, DOB, DOS)
   - Note their IDs, names, or CSS selectors

2. **Update `pages/eligibility_page.py`**
   - Lines 21-31: Form field selectors
   - Lines 34-46: Results field selectors
   - This is the most work, but very straightforward

3. **Special attention to**:
   - **Payer dropdown**: Might be autocomplete, not regular dropdown
   - **Date fields**: Might have date pickers
   - See `SELECTOR_UPDATE_GUIDE.md` for special cases

4. **Test full workflow**:
```powershell
python scripts/run_eligibility.py --input sample/input_eligibility.json --output sample/output_test.json --no-headless
```

**Expected result**: Form fills, submits, and result is parsed (even if not perfect yet).

---

### Step 4: Fine-tune Result Parsing (30-60 minutes)

**Goal**: Accurately extract eligibility results from the response

1. **Run the bot and let it get to results page**

2. **Inspect the results structure**
   - Where is coverage status displayed?
   - Where are deductibles shown?
   - Is there a benefits table?

3. **Update parsing logic in `pages/eligibility_page.py`**:
   - `parse_summary()` - Extract basic fields
   - `parse_benefits_table()` - Parse the benefits table rows
   - `parse_financial_field()` - Handle currency formatting

4. **Test and iterate**:
```powershell
python scripts/run_eligibility.py --input sample/input_eligibility.json --output sample/output_test.json --no-headless
```

5. **Check output**:
```powershell
type sample\output_test.json
```

---

## 🔧 Testing Commands Reference

### Test Login Only (Fastest)
```powershell
cd E:\QuickIntell11\bots
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="E:\QuickIntell11\bots"
python test_login_only.py
```

### Test Full Workflow - JSON Mode
```powershell
cd E:\QuickIntell11\bots
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="E:\QuickIntell11\bots"
python scripts/run_eligibility.py --input sample/input_eligibility.json --output sample/output_test.json --no-headless
```

### Test Full Workflow - Database Mode
```powershell
cd E:\QuickIntell11\bots
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="E:\QuickIntell11\bots"
python scripts/run_eligibility.py --db --no-headless
```

### Run in Headless Mode (Production)
```powershell
python scripts/run_eligibility.py --db
```

---

## 📚 Documentation Reference

| Document | Purpose |
|----------|---------|
| `README.md` | Complete user guide and quickstart |
| `SETUP_GUIDE.md` | Detailed installation and troubleshooting |
| `SELECTOR_UPDATE_GUIDE.md` | **⭐ How to find and update selectors** |
| `PROJECT_SUMMARY.md` | Architecture and implementation details |
| `NEXT_STEPS.md` | This file - your action plan |

---

## 🐛 Troubleshooting

### "Element not found" errors
- **Cause**: Selector doesn't match the actual page
- **Fix**: Re-inspect the element and update the selector
- **Tool**: Chrome DevTools (F12 → Inspector)

### Login succeeds but navigation fails
- **Cause**: Dashboard selectors are wrong
- **Fix**: Update `pages/dashboard_page.py` selectors
- **Tip**: Look for the eligibility link after you log in manually

### Form fills but doesn't submit
- **Cause**: Submit button selector is wrong or there's a validation error
- **Fix**: 
  1. Check submit button selector
  2. Check if all required fields are being filled
  3. Check browser console for JavaScript errors

### Results parse as empty/None
- **Cause**: Result selectors don't match the actual results page
- **Fix**: 
  1. Let bot run to results page
  2. Pause and inspect the actual HTML structure
  3. Update selectors in `eligibility_page.py`

---

## 🎯 Progress Checklist

Track your progress here:

- [x] ✅ Database setup complete
- [x] ✅ Dependencies installed
- [x] ✅ Sample data enqueued
- [x] ✅ Encoding issues fixed
- [ ] 🔲 Login page selectors updated
- [ ] 🔲 Login test passes
- [ ] 🔲 Dashboard navigation selectors updated
- [ ] 🔲 Eligibility form selectors updated
- [ ] 🔲 Form submission works
- [ ] 🔲 Results parsing works
- [ ] 🔲 Full workflow test passes (JSON mode)
- [ ] 🔲 Database workflow test passes (DB mode)
- [ ] 🔲 Ready for production!

---

## 🚀 After All Selectors Are Updated

### Run Production Test
```powershell
# Enqueue multiple requests
python scripts/enqueue_sample.py

# Process them
python scripts/run_eligibility.py --db
```

### Check Database Results
```powershell
docker exec -it availity-pg psql -U user -d availity_rpa
```

```sql
-- View all requests
SELECT id, status, member_id, dos_from, created_at FROM eligibility_requests;

-- View successful results
SELECT er.id, er.member_id, res.coverage_status, res.plan_name 
FROM eligibility_requests er
JOIN eligibility_results res ON res.eligibility_request_id = er.id
WHERE er.status = 'SUCCESS';

-- View benefit lines
SELECT bl.benefit_category, bl.copay_amount, bl.network_tier
FROM eligibility_benefit_lines bl
JOIN eligibility_results res ON bl.eligibility_result_id = res.id
WHERE res.eligibility_request_id = 2;
```

---

## 💡 Pro Tips

1. **Test incrementally** - Don't update all selectors at once. Test after each page.

2. **Use visible browser first** - Always use `--no-headless` while developing. Switch to headless for production.

3. **Save screenshots manually** - Add `driver.save_screenshot("debug.png")` to debug specific steps.

4. **Check artifacts folder** - When errors occur, check `artifacts/` for error screenshots.

5. **Use Chrome DevTools** - The Inspector is your best friend for finding selectors.

6. **Start simple** - Get login working first. Everything else builds on that.

---

## 🎓 Learning Resources

### Selenium Locator Strategies
- **By.ID**: Fastest, most reliable (if available)
- **By.NAME**: Good for form inputs
- **By.CSS_SELECTOR**: Most flexible, preferred
- **By.XPATH**: Powerful but can be brittle

### CSS Selector Cheat Sheet
```css
#elementId              /* By ID */
.className              /* By class */
input[name="username"]  /* By attribute */
form input.required     /* Combination */
[data-testid="submit"]  /* Data attribute */
```

---

**Ready to start?** Begin with Step 1 - Update Login Page Selectors! 🚀

The `SELECTOR_UPDATE_GUIDE.md` has detailed instructions and examples for every step.

