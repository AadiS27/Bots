"""Claim Status page object for form filling and result parsing."""

import re
import time
from datetime import date, datetime
from typing import Optional

from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from core.errors import PortalBusinessError, PortalChangedError, ValidationError
from domain.claim_status_models import ClaimStatusQuery, ClaimStatusReason, ClaimStatusResult

from .base_page import BasePage


class ClaimStatusPage(BasePage):
    """Page object for Availity claim status inquiry form and results."""

    # Actual Availity claim status form selectors (updated from real DOM)
    # Form fields
    PAYER_DROPDOWN = (By.ID, "payer")  # React Select input (different from eligibility which uses "payerId")
    PROVIDER_SELECT_INPUT = (By.ID, "providerExpressEntry")  # React Select for provider
    MEMBER_ID_INPUT = (By.ID, "patientMemberId")  # Patient member ID
    PATIENT_LAST_NAME_INPUT = (By.ID, "patientLastName")  # Patient last name
    PATIENT_FIRST_NAME_INPUT = (By.ID, "patientFirstName")  # Patient first name
    PATIENT_DOB_INPUT = (By.ID, "patientBirthDate")  # Patient date of birth
    SUBSCRIBER_LAST_NAME_INPUT = (By.ID, "subscriberLastName")  # Subscriber last name
    SUBSCRIBER_FIRST_NAME_INPUT = (By.ID, "subscriberFirstName")  # Subscriber first name
    SUBSCRIBER_SAME_AS_PATIENT_CHECKBOX = (By.NAME, "subscriberSameAsPatient")  # Checkbox if subscriber same as patient
    PROVIDER_NPI_INPUT = (By.ID, "providerNpi")  # Provider NPI - may need to verify actual selector

    # Claim information fields
    DOS_FROM_INPUT = (By.ID, "serviceDates-start")  # Service date from
    DOS_TO_INPUT = (By.ID, "serviceDates-end")  # Service date to
    CLAIM_NUMBER_INPUT = (By.ID, "claimNumber")  # Claim number (payer claim ID)
    # Note: Provider claim ID and claim amount fields may be on a different section or modal
    PROVIDER_CLAIM_ID_INPUT = (By.NAME, "providerClaimId")  # May need to verify if exists
    CLAIM_AMOUNT_INPUT = (By.NAME, "claimAmount")  # May need to verify if exists

    # Submit button
    SUBMIT_BUTTON = (By.ID, "submit-by276")  # Submit button (ID may change, fallback to type='submit')
    SUBMIT_BUTTON_FALLBACK = (By.CSS_SELECTOR, "button[type='submit'].btn-primary")  # Fallback selector
    CLEAR_FORM_BUTTON = (By.CSS_SELECTOR, "button[type='reset'], button[contains(text(), 'Clear')]")

    # Results section - TODO: Update based on actual results page structure
    RESULTS_CONTAINER = (By.CSS_SELECTOR, "div[class*='result'], table, .card, [class*='claim-status']")
    RESULTS_GRID = (By.CSS_SELECTOR, "table, [class*='grid'], [class*='table']")  # TODO: Verify actual selector
    RESULTS_ROWS = (By.CSS_SELECTOR, "tbody tr, [class*='row']")  # TODO: Verify actual selector
    STATUS_TEXT = (By.XPATH, "//*[contains(text(), 'Status') or contains(text(), 'Claim Status')]")  # TODO: Verify actual selector
    PAID_AMOUNT_TEXT = (By.XPATH, "//*[contains(text(), 'Paid') or contains(text(), 'Payment')]")  # TODO: Verify actual selector
    ALLOWED_AMOUNT_TEXT = (By.XPATH, "//*[contains(text(), 'Allowed')]")  # TODO: Verify actual selector
    CHECK_NUMBER_TEXT = (By.XPATH, "//*[contains(text(), 'Check') or contains(text(), 'EFT')]")  # TODO: Verify actual selector
    PAYMENT_DATE_TEXT = (By.XPATH, "//*[contains(text(), 'Payment Date')]")  # TODO: Verify actual selector
    REASON_CODES_SECTION = (By.CSS_SELECTOR, "[class*='reason'], [class*='code'], table")  # TODO: Verify actual selector

    # Error messages
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".error-message, .alert-danger, [role='alert'], [class*='error']")
    NO_RESULTS_MESSAGE = (By.XPATH, "//*[contains(text(), 'could not find') or contains(text(), 'no results')]")  # TODO: Verify actual selector

    def __init__(self, driver: WebDriver):
        """
        Initialize claim status page.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def ensure_loaded(self) -> None:
        """
        Ensure the claim status form is loaded.

        Raises:
            PortalChangedError: If form elements not found
        """
        try:
            logger.info("Waiting for claim status form to load...")
            logger.info(f"Current URL: {self.driver.current_url}")

            # First, ensure we're not in an iframe (switch to default content)
            try:
                self.driver.switch_to.default_content()
            except:
                pass

            # Check if form is in an iframe
            from selenium.webdriver.common.by import By as ByLocator
            iframes = self.driver.find_elements(ByLocator.TAG_NAME, "iframe")
            if iframes:
                logger.info(f"Found {len(iframes)} iframe(s), switching to first iframe...")
                self.driver.switch_to.frame(iframes[0])
                logger.info("Switched to iframe")

            # Wait for form elements to appear
            logger.debug("Looking for form elements...")

            # Try multiple approaches to find the form
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    logger.debug(f"Attempt {attempt + 1}/{max_attempts} to find payer dropdown...")
                    # Try by ID first (claim status uses "payer")
                    try:
                        self.wait_for_visible((ByLocator.ID, "payer"), timeout=5)
                        logger.info("Found payer dropdown by ID (payer)!")
                        break
                    except:
                        # Try eligibility selector as fallback
                        try:
                            self.wait_for_visible((ByLocator.ID, "payerId"), timeout=3)
                            logger.info("Found payer dropdown by ID (payerId - eligibility style)!")
                            break
                        except:
                            # Try by CSS with different patterns
                            try:
                                self.wait_for_visible((ByLocator.CSS_SELECTOR, "input.payer-select__input, input[id*='payer']"), timeout=3)
                                logger.info("Found payer field by CSS!")
                                break
                            except:
                                pass
                except Exception as e:
                    if attempt == max_attempts - 1:
                        # Last attempt - try submit button or any input
                        try:
                            logger.debug("Trying to find submit button as fallback...")
                            self.wait_for_visible(self.SUBMIT_BUTTON, timeout=3)
                            logger.info("Found submit button - form is loaded!")
                            break
                        except:
                            # Try to find ANY input field
                            try:
                                self.wait_for_visible((ByLocator.CSS_SELECTOR, "input, textarea"), timeout=3)
                                logger.info("Found some form input - form is loaded!")
                                break
                            except:
                                raise PortalChangedError(
                                    f"Claim status form not found after {max_attempts} attempts. Current URL: {self.driver.current_url}"
                                )
                    else:
                        logger.debug(f"Waiting 1 second before retry...")
                        time.sleep(1)

            logger.info("Claim status form loaded successfully!")

        except Exception as e:
            logger.error(f"Claim status form not loaded. Current URL: {self.driver.current_url}")
            logger.error("Taking screenshot for debugging...")
            raise PortalChangedError(f"Claim status form not loaded: {e}") from e

    def select_payer(self, payer_name: str) -> None:
        """
        Select payer from React Select dropdown with exact matching.

        Args:
            payer_name: Payer name to select

        Raises:
            PortalChangedError: If payer selection fails
        """
        try:
            logger.info(f"Selecting payer: {payer_name}")

            # Try multiple selectors to find the payer dropdown
            payer_input = None
            from selenium.webdriver.common.by import By as ByLocator
            
            # Try by ID first (claim status uses "payer", not "payerId")
            try:
                payer_input = self.wait_for_clickable(self.PAYER_DROPDOWN, timeout=5)
                logger.debug("Found payer dropdown by ID (payer)")
            except:
                # Try eligibility selector as fallback
                try:
                    payer_input = self.wait_for_clickable((ByLocator.ID, "payerId"), timeout=5)
                    logger.debug("Found payer dropdown by ID (payerId - eligibility style)")
                except:
                    # Try by CSS selector (fallback)
                    try:
                        payer_input = self.wait_for_clickable((ByLocator.CSS_SELECTOR, "input[id='payer'], input.payer-select__input"), timeout=5)
                        logger.debug("Found payer dropdown by CSS selector")
                    except:
                        raise PortalChangedError("Could not find payer dropdown with any selector")
            
            if payer_input is None:
                raise PortalChangedError("Payer dropdown element not found")

            # Clear any existing selection first
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Clear the field completely using Ctrl+A and Delete
            payer_input.click()
            time.sleep(0.3)
            payer_input.send_keys(Keys.CONTROL + "a")
            payer_input.send_keys(Keys.DELETE)
            time.sleep(0.3)

            # Now click to open the dropdown
            payer_input.click()

            # Wait for dropdown to open
            try:
                WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                    lambda d: payer_input.get_attribute("aria-expanded") == "true"
                )
            except:
                time.sleep(0.5)

            # Type the payer name to search/filter
            payer_input.send_keys(payer_name)

            # Wait for results to appear
            try:
                WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='option'], [id*='option']"))
                )
            except:
                time.sleep(0.5)

            # Press Enter to select the first/best match
            payer_input.send_keys(Keys.ENTER)

            # Wait for selection to complete
            try:
                WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                    lambda d: payer_input.get_attribute("aria-expanded") != "true"
                )
            except:
                time.sleep(0.5)

            # Verify selection
            time.sleep(0.5)
            selected_value = payer_input.get_attribute("value")
            logger.info(f"Payer selected - field shows: {selected_value}")

        except Exception as e:
            raise PortalChangedError(f"Failed to select payer: {e}") from e

    def fill_search_form(self, query: ClaimStatusQuery) -> None:
        """
        Fill the claim status search form.

        Args:
            query: ClaimStatusQuery with form data

        Raises:
            ValidationError: If required fields are missing
            PortalChangedError: If form elements not found
        """
        try:
            logger.info(f"Filling claim status form for request ID: {query.request_id}")

            # Select payer using React Select
            self.select_payer(query.payer_name)

            # Wait for form fields to appear after payer selection
            logger.info("Waiting for form fields to appear after payer selection...")
            time.sleep(2)  # Allow form to populate

            # Provider Select - React Select (may be pre-filled)
            try:
                if self.exists(self.PROVIDER_SELECT_INPUT, timeout=3):
                    # Provider might be pre-selected, check if we need to change it
                    logger.debug("Provider select field found (may be pre-filled)")
                    # TODO: If provider needs to be changed, use React Select pattern similar to payer
            except:
                logger.debug("Provider select field not found, skipping...")

            # Patient Information
            # Member ID (required field)
            if query.member_id:
                try:
                    if self.exists(self.MEMBER_ID_INPUT, timeout=3):
                        self.type(self.MEMBER_ID_INPUT, query.member_id, clear_first=True)
                        logger.debug(f"Member ID: {query.member_id}")
                except Exception as e:
                    logger.warning(f"Could not fill member ID: {e}, continuing...")

            # Patient Last Name (required field)
            if query.patient_last_name:
                try:
                    if self.exists(self.PATIENT_LAST_NAME_INPUT, timeout=3):
                        self.type(self.PATIENT_LAST_NAME_INPUT, query.patient_last_name, clear_first=True)
                        logger.debug(f"Patient Last Name: {query.patient_last_name}")
                except Exception as e:
                    logger.warning(f"Could not fill patient last name: {e}, continuing...")

            # Patient First Name (required field)
            if query.patient_first_name:
                try:
                    if self.exists(self.PATIENT_FIRST_NAME_INPUT, timeout=3):
                        self.type(self.PATIENT_FIRST_NAME_INPUT, query.patient_first_name, clear_first=True)
                        logger.debug(f"Patient First Name: {query.patient_first_name}")
                except Exception as e:
                    logger.warning(f"Could not fill patient first name: {e}, continuing...")

            # Patient DOB (required field)
            if query.patient_dob:
                try:
                    if self.exists(self.PATIENT_DOB_INPUT, timeout=3):
                        dob_str = query.patient_dob.strftime("%m/%d/%Y")
                        from selenium.webdriver.common.keys import Keys
                        dob_input = self.wait_for_visible(self.PATIENT_DOB_INPUT, timeout=3)
                        dob_input.send_keys(Keys.CONTROL + "a")
                        dob_input.send_keys(Keys.DELETE)
                        dob_input.send_keys(dob_str)
                        logger.debug(f"Patient DOB: {dob_str}")
                except Exception as e:
                    logger.warning(f"Could not fill patient DOB: {e}, continuing...")

            # Subscriber Information
            # Subscriber Information
            # First, handle the checkbox if subscriber is different from patient
            if not query.subscriber_same_as_patient:
                # Uncheck "Subscriber same as patient" checkbox if needed
                try:
                    if self.exists(self.SUBSCRIBER_SAME_AS_PATIENT_CHECKBOX, timeout=5):
                        checkbox = self.wait_for_visible(self.SUBSCRIBER_SAME_AS_PATIENT_CHECKBOX, timeout=5)
                        if checkbox.is_selected():
                            checkbox.click()
                            logger.debug("Unchecked 'Subscriber same as patient' checkbox")
                            time.sleep(0.5)  # Wait for fields to appear
                except Exception as e:
                    logger.debug(f"Subscriber same as patient checkbox not found or error: {e}, continuing...")

            # Fill subscriber fields if provided (always try to fill, not just when checkbox is unchecked)
            if query.subscriber_last_name:
                try:
                    subscriber_last_name_input = self.wait_for_visible(self.SUBSCRIBER_LAST_NAME_INPUT, timeout=10)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", subscriber_last_name_input)
                    time.sleep(0.3)
                    self.type(self.SUBSCRIBER_LAST_NAME_INPUT, query.subscriber_last_name, clear_first=True)
                    logger.info(f"Subscriber Last Name filled: {query.subscriber_last_name}")
                except Exception as e:
                    logger.warning(f"Could not fill subscriber last name: {e}, continuing...")

            if query.subscriber_first_name:
                try:
                    subscriber_first_name_input = self.wait_for_visible(self.SUBSCRIBER_FIRST_NAME_INPUT, timeout=10)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", subscriber_first_name_input)
                    time.sleep(0.3)
                    self.type(self.SUBSCRIBER_FIRST_NAME_INPUT, query.subscriber_first_name, clear_first=True)
                    logger.info(f"Subscriber First Name filled: {query.subscriber_first_name}")
                except Exception as e:
                    logger.warning(f"Could not fill subscriber first name: {e}, continuing...")

            # Provider NPI
            if query.provider_npi:
                try:
                    npi_input = self.wait_for_visible(self.PROVIDER_NPI_INPUT, timeout=10)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", npi_input)
                    time.sleep(0.3)
                    # Clear existing value using multiple methods
                    current_value = npi_input.get_attribute("value")
                    if current_value:
                        logger.debug(f"Clearing existing NPI value: {current_value}")
                        # Method 1: JavaScript clear
                        self.driver.execute_script("arguments[0].value = '';", npi_input)
                        self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", npi_input)
                        time.sleep(0.2)
                        # Method 2: Selenium clear
                        npi_input.clear()
                        time.sleep(0.2)
                        # Method 3: Keyboard clear
                        from selenium.webdriver.common.keys import Keys
                        npi_input.send_keys(Keys.CONTROL + "a")
                        time.sleep(0.1)
                        npi_input.send_keys(Keys.DELETE)
                        time.sleep(0.1)
                    # Now fill the new value
                    self.type(self.PROVIDER_NPI_INPUT, query.provider_npi, clear_first=False)  # Already cleared above
                    logger.info(f"Provider NPI filled: {query.provider_npi}")
                except Exception as e:
                    logger.warning(f"Could not fill provider NPI: {e}, continuing...")

            # Claim Information
            # Service Dates (DOS) - required fields
            try:
                if self.exists(self.DOS_FROM_INPUT, timeout=3):
                    dos_from_str = query.dos_from.strftime("%m/%d/%Y")
                    from selenium.webdriver.common.keys import Keys
                    date_input = self.wait_for_visible(self.DOS_FROM_INPUT, timeout=3)
                    date_input.send_keys(Keys.CONTROL + "a")
                    date_input.send_keys(Keys.DELETE)
                    date_input.send_keys(dos_from_str)
                    logger.debug(f"DOS From: {dos_from_str}")

                    # DOS To (if provided, otherwise use same as from date)
                    dos_to_date = query.dos_to if query.dos_to else query.dos_from
                    if self.exists(self.DOS_TO_INPUT, timeout=3):
                        dos_to_str = dos_to_date.strftime("%m/%d/%Y")
                        date_to_input = self.wait_for_visible(self.DOS_TO_INPUT, timeout=3)
                        date_to_input.send_keys(Keys.CONTROL + "a")
                        date_to_input.send_keys(Keys.DELETE)
                        date_to_input.send_keys(dos_to_str)
                        logger.debug(f"DOS To: {dos_to_str}")
            except Exception as e:
                logger.warning(f"Could not fill service dates: {e}, continuing...")

            # Claim Number (Payer Claim ID) - optional
            if query.payer_claim_id:
                try:
                    if self.exists(self.CLAIM_NUMBER_INPUT, timeout=3):
                        self.type(self.CLAIM_NUMBER_INPUT, query.payer_claim_id, clear_first=True)
                        logger.debug(f"Claim Number (Payer Claim ID): {query.payer_claim_id}")
                except Exception as e:
                    logger.warning(f"Could not fill claim number: {e}, continuing...")

            # Provider Claim ID (if provided and field exists)
            if query.provider_claim_id:
                try:
                    if self.exists(self.PROVIDER_CLAIM_ID_INPUT, timeout=3):
                        self.type(self.PROVIDER_CLAIM_ID_INPUT, query.provider_claim_id, clear_first=True)
                        logger.debug(f"Provider Claim ID: {query.provider_claim_id}")
                except Exception as e:
                    logger.debug(f"Provider claim ID field not found or error: {e}, continuing...")

            # Claim Amount (if provided and field exists)
            if query.claim_amount:
                try:
                    if self.exists(self.CLAIM_AMOUNT_INPUT, timeout=3):
                        amount_str = f"{query.claim_amount:.2f}"
                        self.type(self.CLAIM_AMOUNT_INPUT, amount_str, clear_first=True)
                        logger.debug(f"Claim Amount: {amount_str}")
                except Exception as e:
                    logger.debug(f"Claim amount field not found or error: {e}, continuing...")

            logger.info("Form filled successfully")

        except Exception as e:
            logger.error(f"Failed to fill form: {e}")
            raise PortalChangedError(f"Form filling failed: {e}") from e

    def submit_and_wait(self, timeout: int = 60) -> None:
        """
        Submit the claim status form and wait for results.

        Args:
            timeout: Maximum wait time in seconds

        Raises:
            PortalBusinessError: If portal returns a business error
            PortalChangedError: If results don't load
        """
        try:
            logger.info("Submitting claim status form")

            # Try primary submit button selector first, fallback to generic
            submit_button = None
            try:
                submit_button = self.wait_for_clickable(self.SUBMIT_BUTTON, timeout=5)
                logger.debug("Found submit button by ID")
            except:
                logger.debug("Primary submit button not found, trying fallback...")
                submit_button = self.wait_for_clickable(self.SUBMIT_BUTTON_FALLBACK, timeout=5)
                logger.debug("Found submit button by fallback selector")

            # Wait until button is enabled
            from selenium.webdriver.support.ui import WebDriverWait
            wait = WebDriverWait(self.driver, 5, poll_frequency=0.2)
            wait.until(lambda d: submit_button.is_enabled())

            # Scroll into view
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button)

            # Click submit
            try:
                submit_button.click()
                logger.debug("Submit button clicked")
            except Exception as e1:
                logger.warning(f"Regular click failed: {e1}, trying JavaScript click...")
                self.driver.execute_script("arguments[0].click();", submit_button)
                logger.debug("Submit button clicked via JavaScript")

            # Wait for results to load - give it plenty of time
            logger.info("Waiting for claim status results to load...")
            time.sleep(5)  # Initial wait for page transition and processing
            
            # Wait for page to stabilize (no loading indicators)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            # Wait for any loading spinners to disappear
            try:
                WebDriverWait(self.driver, 30, poll_frequency=1).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='loading'], [class*='spinner'], [class*='loader']"))
                )
                logger.debug("Loading indicators disappeared")
            except:
                logger.debug("No loading indicators found or timeout waiting for them")
            
            # Additional wait for results to fully render
            logger.info("Waiting additional time for results to fully render...")
            time.sleep(10)  # Give plenty of time for results to load
            
            # Check for error messages first
            if self.exists(self.ERROR_MESSAGE, timeout=5):
                error_text = self.get_text(self.ERROR_MESSAGE)
                logger.warning(f"Portal returned error: {error_text}")
                raise PortalBusinessError(f"Portal error: {error_text}")

            # Check for "no results" message
            if self.exists(self.NO_RESULTS_MESSAGE, timeout=5):
                logger.info("No results found message detected")
                # This is not necessarily an error - it's a valid result

            # Wait for results container (may be empty results, table, or detail view)
            logger.info("Looking for results container...")
            try:
                # Try to find results container with longer timeout
                self.wait_for_visible(self.RESULTS_CONTAINER, timeout=30)
                logger.info("Results container loaded")
            except:
                # Results container might not appear if no results - check for any result indicators
                logger.info("Results container not found - checking for other result indicators...")
                # Check if we're still on the form page (might indicate submission failed)
                if self.exists(self.SUBMIT_BUTTON, timeout=2) or self.exists(self.SUBMIT_BUTTON_FALLBACK, timeout=2):
                    logger.warning("Still on form page - submission may have failed")
                else:
                    logger.info("Not on form page - results may be loading or displayed differently")
            
            # Final wait to ensure everything is rendered
            logger.info("Final wait to ensure all content is rendered...")
            time.sleep(5)

        except PortalBusinessError:
            raise
        except Exception as e:
            logger.warning(f"Error waiting for results: {e}")
            # Don't raise - might be no results scenario

    def parse_grid_and_detail(self, query: ClaimStatusQuery) -> ClaimStatusResult:
        """
        Parse claim status results from the page.

        The results may be in a grid/table format or detail view.
        This method attempts to extract all available information from the results page.

        Args:
            query: Original query

        Returns:
            ClaimStatusResult object
        """
        logger.info("Parsing claim status results from page...")
        
        # Get page source for debugging
        try:
            page_text = self.driver.page_source
            logger.debug(f"Page source length: {len(page_text)} characters")
        except:
            pass

        result = ClaimStatusResult(
            request_id=query.request_id,
            transaction_id=None,
            high_level_status=None,
            status_code=None,
            finalized_date=None,
            service_dates=None,
            claim_number=None,
            member_name=None,
            member_id=None,
            billed_amount=None,
            paid_amount=None,
            check_or_eft_number=None,
            payment_date=None,
            reason_codes=[],
            raw_response_html_path=None,  # Will be set by bot if saving HTML
        )

        try:
            from selenium.webdriver.common.by import By
            
            # First, try to find and parse results table/grid
            logger.info("Looking for results table/grid...")
            if self.exists(self.RESULTS_GRID, timeout=5):
                logger.info("Found results grid/table, parsing...")
                rows = self.find_elements(self.RESULTS_ROWS, timeout=5)
                logger.info(f"Found {len(rows)} result rows")
                
                if rows:
                    # Try to parse table structure
                    try:
                        # Get table headers to understand structure
                        headers = self.driver.find_elements(By.CSS_SELECTOR, "thead th, table th, [class*='header']")
                        header_texts = [h.text.strip() for h in headers if h.text.strip()]
                        logger.info(f"Table headers found: {header_texts}")
                        
                        # Create a mapping of column indices to field names
                        # Note: The actual data row may have fewer columns than headers due to merged cells or different structure
                        column_map = {}
                        for i, header in enumerate(header_texts):
                            header_lower = header.lower().replace('\n', ' ')
                            if 'status' in header_lower and 'claim' not in header_lower and 'cs' not in header_lower:
                                column_map['status'] = i
                            elif 'paid' in header_lower and 'amount' in header_lower:
                                column_map['paid_amount'] = i
                            elif 'billed' in header_lower:
                                column_map['allowed_amount'] = i  # Billed amount maps to allowed_amount
                            elif 'allowed' in header_lower:
                                column_map['allowed_amount'] = i
                            elif 'date' in header_lower and 'final' in header_lower:
                                column_map['status_date'] = i
                            elif 'claim' in header_lower and '#' in header_lower:
                                column_map['claim_number'] = i
                        
                        # Also try to map based on data row structure if headers don't match
                        # Common pattern: Status is usually first column in data rows
                        if 'status' not in column_map:
                            column_map['status'] = 0  # Status is typically first column
                        
                        # Find the first actual data row (skip header rows and buttons)
                        data_row = None
                        for row in rows:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if not cells:
                                cells = row.find_elements(By.CSS_SELECTOR, "[class*='cell'], div")
                            
                            cell_texts = [cell.text.strip() for cell in cells if cell.text.strip()]
                            # Skip rows that are clearly not data (buttons, headers, etc.)
                            if cell_texts and len(cell_texts) > 2:
                                # Check if this looks like a data row (has status, amounts, dates, etc.)
                                row_text = ' '.join(cell_texts).lower()
                                if any(keyword in row_text for keyword in ['paid', 'denied', 'pending', 'received', '$', '/']):
                                    data_row = row
                                    logger.info(f"Found data row with {len(cell_texts)} cells: {cell_texts[:5]}...")  # Log first 5 cells
                                    break
                        
                        if data_row:
                            cells = data_row.find_elements(By.TAG_NAME, "td")
                            if not cells:
                                cells = data_row.find_elements(By.CSS_SELECTOR, "[class*='cell'], div")
                            
                            cell_texts = [cell.text.strip() for cell in cells if cell.text.strip()]
                            logger.info(f"Parsing data row with {len(cell_texts)} cells")
                            
                            # Extract data based on table structure: 
                            # 0=Status, 1=Finalized Date, 2=Service Dates, 3=Claim#, 4=Member Name, 5=Member ID, 6=Billed Amount, 7=Paid Amount
                            
                            # Status (first cell)
                            if len(cell_texts) > 0 and not result.high_level_status:
                                first_cell = cell_texts[0].strip()
                                first_lower = first_cell.lower()
                                if any(status in first_lower for status in ['paid', 'denied', 'pending', 'received', 'processed', 'approved', 'finalized']):
                                    result.high_level_status = first_cell
                                    logger.info(f"Found status from first cell: {first_cell}")
                            
                            # Finalized Date (second cell)
                            if len(cell_texts) > 1 and not result.finalized_date:
                                second_cell = cell_texts[1].strip()
                                try:
                                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', second_cell)
                                    if date_match:
                                        date_str = date_match.group(1)
                                        parts = date_str.split('/')
                                        if len(parts) == 3:
                                            month, day, year = parts
                                            if len(year) == 2:
                                                year = '20' + year
                                            parsed_date = datetime.strptime(f"{month}/{day}/{year}", "%m/%d/%Y").date()
                                            result.finalized_date = parsed_date
                                            logger.info(f"Found finalized date from second cell: {parsed_date}")
                                except:
                                    pass
                            
                            # Service Dates (third cell)
                            if len(cell_texts) > 2 and not result.service_dates:
                                third_cell = cell_texts[2].strip()
                                result.service_dates = third_cell.replace('\n', ' - ')  # Handle multiple dates
                                logger.info(f"Found service dates: {result.service_dates}")
                            
                            # Claim Number (fourth cell)
                            if len(cell_texts) > 3 and not result.claim_number:
                                result.claim_number = cell_texts[3].strip()
                                logger.info(f"Found claim number: {result.claim_number}")
                            
                            # Member Name (fifth cell)
                            if len(cell_texts) > 4 and not result.member_name:
                                result.member_name = cell_texts[4].strip()
                                logger.info(f"Found member name: {result.member_name}")
                            
                            # Member ID (sixth cell)
                            if len(cell_texts) > 5 and not result.member_id:
                                result.member_id = cell_texts[5].strip()
                                logger.info(f"Found member ID: {result.member_id}")
                            
                            # Billed Amount (seventh cell, index 6)
                            if len(cell_texts) > 6 and not result.billed_amount:
                                billed_text = cell_texts[6].strip()
                                if '$' in billed_text:
                                    try:
                                        amount = float(re.sub(r'[$,]', '', billed_text))
                                        result.billed_amount = amount
                                        logger.info(f"Found billed amount from cell 6: ${amount}")
                                    except:
                                        pass
                            
                            # Paid Amount (eighth cell, index 7)
                            if len(cell_texts) > 7 and not result.paid_amount:
                                paid_text = cell_texts[7].strip()
                                if '$' in paid_text:
                                    try:
                                        amount = float(re.sub(r'[$,]', '', paid_text))
                                        result.paid_amount = amount
                                        logger.info(f"Found paid amount from cell 7: ${amount}")
                                    except:
                                        pass
                            
                            # Fallback: Try column mapping if direct indexing didn't work
                            for field, col_idx in column_map.items():
                                if col_idx < len(cell_texts):
                                    value = cell_texts[col_idx].strip()
                                    if field == 'status' and not result.high_level_status:
                                        value_lower = value.lower()
                                        if any(status in value_lower for status in ['paid', 'denied', 'pending', 'received', 'processed', 'approved', 'finalized']):
                                            result.high_level_status = value
                                            logger.info(f"Found status from table column {col_idx}: {value}")
                                    elif field == 'paid_amount' and not result.paid_amount:
                                        try:
                                            amount = float(re.sub(r'[$,]', '', value))
                                            result.paid_amount = amount
                                            logger.info(f"Found paid amount from table column {col_idx}: ${amount}")
                                        except:
                                            pass
                                    elif field == 'allowed_amount' and not result.billed_amount:
                                        try:
                                            amount = float(re.sub(r'[$,]', '', value))
                                            result.billed_amount = amount
                                            logger.info(f"Found billed amount from table column {col_idx}: ${amount}")
                                        except:
                                            pass
                                    elif field == 'status_date' and not result.finalized_date:
                                        try:
                                            date_text = value.split('\n')[0] if '\n' in value else value
                                            date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', date_text)
                                            if date_match:
                                                date_str = date_match.group(1)
                                                if '/' in date_str:
                                                    parts = date_str.split('/')
                                                    if len(parts) == 3:
                                                        month, day, year = parts
                                                        if len(year) == 2:
                                                            year = '20' + year
                                                        parsed_date = datetime.strptime(f"{month}/{day}/{year}", "%m/%d/%Y").date()
                                                        result.finalized_date = parsed_date
                                                        logger.info(f"Found finalized date from table: {parsed_date}")
                                        except:
                                            pass
                                    elif field == 'claim_number' and not result.claim_number:
                                        result.claim_number = value
                                        logger.info(f"Found claim number from table column {col_idx}: {value}")
                    except Exception as e:
                        logger.warning(f"Error parsing table row: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())

            # Try to find status information in various formats
            logger.info("Searching for status information...")
            status_patterns = [
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'status')]"),
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'claim status')]"),
                (By.CSS_SELECTOR, "[class*='status'], [id*='status']"),
            ]
            
            for pattern in status_patterns:
                try:
                    elements = self.driver.find_elements(*pattern)
                    for elem in elements[:5]:  # Check first 5 matches
                        text = elem.text.strip()
                        if text and len(text) < 100:  # Reasonable status text length
                            text_lower = text.lower()
                            if 'status' in text_lower or any(s in text_lower for s in ['paid', 'denied', 'pending', 'received']):
                                if result.high_level_status is None:
                                    result.high_level_status = text
                                    logger.info(f"Found status from pattern: {text}")
                                    break
                except:
                    continue

            # Try to find amounts (paid, billed, etc.)
            logger.info("Searching for payment amounts...")
            amount_patterns = [
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'paid')]"),
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'billed')]"),
                (By.XPATH, "//*[contains(text(), '$')]"),
            ]
            
            for pattern in amount_patterns:
                try:
                    elements = self.driver.find_elements(*pattern)
                    for elem in elements[:10]:  # Check first 10 matches
                        text = elem.text.strip()
                        # Look for dollar amounts
                        amounts = re.findall(r'\$[\d,]+\.?\d*', text)
                        for amount_str in amounts:
                            try:
                                amount = float(re.sub(r'[$,]', '', amount_str))
                                if 'paid' in text.lower() and result.paid_amount is None:
                                    result.paid_amount = amount
                                    logger.info(f"Found paid amount: ${amount}")
                                elif 'billed' in text.lower() and result.billed_amount is None:
                                    result.billed_amount = amount
                                    logger.info(f"Found billed amount: ${amount}")
                            except:
                                pass
                except:
                    continue

            # Try to find check/EFT number
            logger.info("Searching for check/EFT number...")
            check_patterns = [
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'check')]"),
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'eft')]"),
            ]
            
            for pattern in check_patterns:
                try:
                    elements = self.driver.find_elements(*pattern)
                    for elem in elements[:5]:
                        text = elem.text.strip()
                        # Look for alphanumeric check numbers
                        check_match = re.search(r'(?:check|eft)[\s:]*([A-Z0-9-]+)', text, re.IGNORECASE)
                        if check_match:
                            result.check_or_eft_number = check_match.group(1)
                            logger.info(f"Found check/EFT number: {result.check_or_eft_number}")
                            break
                except:
                    continue

            # Try to find dates (finalized date, payment date)
            logger.info("Searching for dates...")
            date_patterns = [
                (By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'date')]"),
                (By.CSS_SELECTOR, "[class*='date'], [id*='date']"),
            ]
            
            for pattern in date_patterns:
                try:
                    elements = self.driver.find_elements(*pattern)
                    for elem in elements[:10]:
                        text = elem.text.strip()
                        # Look for date patterns MM/DD/YYYY or similar
                        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
                        if date_match:
                            try:
                                date_str = date_match.group(1)
                                # Try to parse date
                                if '/' in date_str:
                                    parts = date_str.split('/')
                                    if len(parts) == 3:
                                        month, day, year = parts
                                        if len(year) == 2:
                                            year = '20' + year
                                        parsed_date = datetime.strptime(f"{month}/{day}/{year}", "%m/%d/%Y").date()
                                        
                                        if 'payment' in text.lower() and result.payment_date is None:
                                            result.payment_date = parsed_date
                                            logger.info(f"Found payment date: {parsed_date}")
                                        elif 'final' in text.lower() and result.finalized_date is None:
                                            result.finalized_date = parsed_date
                                            logger.info(f"Found finalized date: {parsed_date}")
                            except:
                                pass
                except:
                    continue

            # Try to find reason codes
            logger.info("Searching for reason codes...")
            if self.exists(self.REASON_CODES_SECTION, timeout=3):
                logger.info("Found reason codes section")
                try:
                    # Look for code patterns (CARC, RARC, LOCAL codes)
                    code_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'CARC') or contains(text(), 'RARC') or contains(text(), 'LOCAL')]")
                    for elem in code_elements:
                        text = elem.text.strip()
                        # Try to extract code type and code
                        code_match = re.search(r'(CARC|RARC|LOCAL)[\s:]*(\d+)', text, re.IGNORECASE)
                        if code_match:
                            code_type = code_match.group(1).upper()
                            code = code_match.group(2)
                            # Try to get description from nearby text
                            description = text.replace(code_type, '').replace(code, '').strip(' :,-')
                            if not description:
                                description = None
                            
                            reason = ClaimStatusReason(
                                code_type=code_type,
                                code=code,
                                description=description
                            )
                            result.reason_codes.append(reason)
                            logger.info(f"Found reason code: {code_type} {code} - {description}")
                except Exception as e:
                    logger.warning(f"Error parsing reason codes: {e}")

            # Try to extract Transaction ID from page
            try:
                transaction_id_patterns = [
                    (By.XPATH, "//*[contains(text(), 'Transaction ID') or contains(text(), 'transaction')]"),
                    (By.CSS_SELECTOR, "[class*='transaction'], [id*='transaction']"),
                ]
                for pattern in transaction_id_patterns:
                    try:
                        elements = self.driver.find_elements(*pattern)
                        for elem in elements[:3]:
                            text = elem.text.strip()
                            # Look for UUID pattern
                            uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', text, re.IGNORECASE)
                            if uuid_match:
                                result.transaction_id = uuid_match.group(1)
                                logger.info(f"Found transaction ID: {result.transaction_id}")
                                break
                        if result.transaction_id:
                            break
                    except:
                        continue
            except:
                pass

            # Log summary of what was found
            logger.info("=== Parsing Summary ===")
            logger.info(f"Transaction ID: {result.transaction_id}")
            logger.info(f"Status: {result.high_level_status}")
            logger.info(f"Finalized Date: {result.finalized_date}")
            logger.info(f"Service Dates: {result.service_dates}")
            logger.info(f"Claim Number: {result.claim_number}")
            logger.info(f"Member Name: {result.member_name}")
            logger.info(f"Member ID: {result.member_id}")
            logger.info(f"Billed Amount: ${result.billed_amount}" if result.billed_amount else "Billed Amount: None")
            logger.info(f"Paid Amount: ${result.paid_amount}" if result.paid_amount else "Paid Amount: None")
            logger.info(f"Check/EFT Number: {result.check_or_eft_number}")
            logger.info(f"Payment Date: {result.payment_date}")
            logger.info(f"Reason Codes: {len(result.reason_codes)}")
            logger.info("======================")

        except Exception as e:
            logger.warning(f"Error parsing results: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Return result with whatever we found

        logger.info(f"Completed parsing result for request {query.request_id}")
        return result

    def parse_result(self, query: ClaimStatusQuery) -> ClaimStatusResult:
        """
        Parse complete claim status result from the page.

        This is the main entry point for parsing.

        Args:
            query: Original query

        Returns:
            ClaimStatusResult object
        """
        return self.parse_grid_and_detail(query)

