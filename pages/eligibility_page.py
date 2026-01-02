"""Eligibility page object for form filling and result parsing."""

import re
import time
from datetime import date, datetime
from typing import Optional

from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from core.errors import PortalBusinessError, PortalChangedError, ValidationError
from domain import EligibilityBenefitLine, EligibilityRequest, EligibilityResult

from .base_page import BasePage


class EligibilityPage(BasePage):
    """Page object for Availity eligibility check form and results."""

    # Actual Availity eligibility form selectors
    # Form fields
    PAYER_DROPDOWN = (By.ID, "payerId")  # React Select input
    PROVIDER_SEARCH_DROPDOWN = (By.CSS_SELECTOR, "input[aria-label*='Provider'], input[id*='provider'], input[placeholder*='Provider']")  # Provider search field (React Select)
    PATIENT_SEARCH_OPTION = (By.ID, "patientSearchOption")  # Patient Search Option React Select
    
    # Tab selectors
    MULTIPLE_PATIENTS_TAB = (By.XPATH, "//button[contains(@class, 'MuiTab-root') and contains(text(), 'Multiple Patients')]")
    SINGLE_PATIENT_TAB = (By.XPATH, "//button[contains(@class, 'MuiTab-root') and contains(text(), 'Single Patient')]")
    
    # Single patient fields
    MEMBER_ID_INPUT = (By.NAME, "memberId")  # Member ID field
    PATIENT_LAST_NAME_INPUT = (By.NAME, "patientLastName")  # Patient last name
    PATIENT_FIRST_NAME_INPUT = (By.NAME, "patientFirstName")  # Patient first name
    PATIENT_DOB_INPUT = (By.ID, "patientBirthDatefield-picker")  # Patient date of birth
    SUBMIT_ANOTHER_PATIENT_CHECKBOX = (By.NAME, "shouldSubmitAnotherPatient")  # Checkbox to submit another patient
    
    # Multiple patients field
    MULTIPLE_PATIENTS_TEXTAREA = (By.ID, "multiPatients-field")  # Multiple patients textarea
    MULTIPLE_PATIENTS_TEXTAREA_ALT = (By.NAME, "multiPatients")  # Alternative selector by name
    
    # Service information
    DATE_OF_SERVICE = (By.ID, "asOfDate-picker")  # Date picker input
    SERVICE_TYPE_DROPDOWN = (By.ID, "serviceType")  # Service type React Select
    PROVIDER_NPI_INPUT = (By.NAME, "providerNpi")  # Provider NPI field
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")  # Submit button

    # Results section - TODO: These need to be updated after seeing actual results
    RESULTS_CONTAINER = (By.CSS_SELECTOR, "div[class*='result'], table, .card")  # Generic results container
    COVERAGE_STATUS = (By.XPATH, "//*[contains(text(), 'Coverage') or contains(text(), 'Status')]")
    PLAN_NAME = (By.XPATH, "//*[contains(text(), 'Plan')]")
    PLAN_TYPE = (By.XPATH, "//*[contains(text(), 'Plan Type')]")
    COVERAGE_DATES = (By.XPATH, "//*[contains(text(), 'Coverage') and contains(text(), 'Date')]")
    DEDUCTIBLE_INDIVIDUAL = (By.XPATH, "//*[contains(text(), 'Deductible')]")
    DEDUCTIBLE_REMAINING = (By.XPATH, "//*[contains(text(), 'Deductible Remaining')]")
    OOP_MAX_INDIVIDUAL = (By.XPATH, "//*[contains(text(), 'Out-of-Pocket') and contains(text(), 'Individual')]")
    OOP_MAX_FAMILY = (By.XPATH, "//*[contains(text(), 'Out-of-Pocket') and contains(text(), 'Family')]")
    BENEFITS_TABLE = (By.CSS_SELECTOR, "table, [class*='benefit'], [class*='table']")
    BENEFITS_ROWS = (By.CSS_SELECTOR, "tbody tr, [class*='benefit'] tr")
    
    # Patient history sidebar selectors
    PATIENT_HISTORY_SIDEBAR = (By.CSS_SELECTOR, "[class*='sidebar'], [class*='patient'], [class*='history']")  # Patient history sidebar
    PATIENT_HISTORY_ITEM = (By.XPATH, "//div[contains(@class, 'patient') or contains(text(), ',')]")  # Individual patient items in history
    PATIENT_HISTORY_NAME = (By.XPATH, ".//*[contains(text(), ',')]")  # Patient name in history item
    
    # Detailed eligibility result fields (from second image)
    MEMBER_STATUS = (By.XPATH, "//*[contains(text(), 'Member Status') or contains(text(), 'Active Coverage')]")
    MEMBER_DOB = (By.XPATH, "//*[contains(text(), 'Date of Birth')]")
    MEMBER_GENDER = (By.XPATH, "//*[contains(text(), 'Gender')]")
    RELATIONSHIP_TO_SUBSCRIBER = (By.XPATH, "//*[contains(text(), 'Relationship to Subscriber')]")
    MEMBER_ID_RESULT = (By.XPATH, "//*[contains(text(), 'Member ID')]")
    SUBSCRIBER_NAME = (By.XPATH, "//*[contains(text(), 'Subscriber')]")
    GROUP_NUMBER = (By.XPATH, "//*[contains(text(), 'Group Number')]")
    GROUP_NAME = (By.XPATH, "//*[contains(text(), 'Group Name')]")
    PLAN_NUMBER = (By.XPATH, "//*[contains(text(), 'Plan Number')]")
    PLAN_BEGIN_DATE = (By.XPATH, "//*[contains(text(), 'Plan Begin Date')]")
    ELIGIBILITY_BEGIN_DATE = (By.XPATH, "//*[contains(text(), 'Eligibility Begin Date')]")
    PAYER_NAME_RESULT = (By.XPATH, "//*[contains(text(), 'Payer:')]")
    
    # Error messages
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".error-message, .alert-danger, [role='alert']")

    def __init__(self, driver: WebDriver):
        """
        Initialize eligibility page.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def reset_form(self) -> None:
        """
        Reset/navigate back to the eligibility form after results.
        
        This is needed for multiple requests - after getting results, we need to go back to the form.
        """
        try:
            from selenium.webdriver.common.by import By as ByLocator
            
            # Save current URL
            current_url = self.driver.current_url
            logger.info(f"Resetting form from URL: {current_url}")
            
            # Switch to default content first
            try:
                self.driver.switch_to.default_content()
                logger.debug("Switched to default content")
            except:
                pass
            
            # Check if we're on results page - check in both default content and iframe
            is_on_results = False
            try:
                # Check in default content
                if self.exists(self.RESULTS_CONTAINER, timeout=1) or self.exists(self.ERROR_MESSAGE, timeout=1):
                    is_on_results = True
                    logger.info("Detected results page in default content")
                else:
                    # Check in iframe
                    iframes = self.driver.find_elements(ByLocator.TAG_NAME, "iframe")
                    if iframes:
                        try:
                            self.driver.switch_to.frame(iframes[0])
                            if self.exists(self.RESULTS_CONTAINER, timeout=1) or self.exists(self.ERROR_MESSAGE, timeout=1):
                                is_on_results = True
                                logger.info("Detected results page in iframe")
                            self.driver.switch_to.default_content()
                        except:
                            self.driver.switch_to.default_content()
            except:
                pass
            
            if is_on_results:
                logger.info("Attempting to reset form...")
                
                # Try to find and click reset button in iframe first (most common case)
                iframes = self.driver.find_elements(ByLocator.TAG_NAME, "iframe")
                if iframes:
                    try:
                        self.driver.switch_to.frame(iframes[0])
                        # Look for reset buttons
                        reset_buttons = [
                            (ByLocator.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'new')]"),
                            (ByLocator.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'another')]"),
                            (ByLocator.CSS_SELECTOR, "button[aria-label*='New'], button[aria-label*='Another']"),
                            (ByLocator.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'new')]"),
                        ]
                        
                        for button_locator in reset_buttons:
                            try:
                                if self.exists(button_locator, timeout=2):
                                    logger.info(f"Found reset button in iframe, clicking...")
                                    self.click(button_locator, timeout=3)
                                    self.driver.switch_to.default_content()
                                    
                                    # Wait longer for form to fully reload and be ready
                                    logger.info("Waiting for form to reload after reset...")
                                    time.sleep(8)  # Increased wait time for React app to fully reload
                                    
                                    # Verify form is ready by checking for payer field in iframe
                                    iframes_check = self.driver.find_elements(ByLocator.TAG_NAME, "iframe")
                                    if iframes_check:
                                        try:
                                            self.driver.switch_to.frame(iframes_check[0])
                                            # Wait for payer field to be present (confirms form is loaded)
                                            if self.exists((ByLocator.ID, "payerId"), timeout=5):
                                                logger.info("Form reset successful - payer field is ready")
                                            else:
                                                logger.warning("Payer field not found after reset, but continuing...")
                                            self.driver.switch_to.default_content()
                                        except:
                                            self.driver.switch_to.default_content()
                                    
                                    logger.info("Form reset complete")
                                    return
                            except:
                                continue
                        
                        self.driver.switch_to.default_content()
                    except Exception as e:
                        self.driver.switch_to.default_content()
                        logger.debug(f"Error checking iframe for reset button: {e}")
                
                # If no reset button found, try to reload the eligibility page URL
                # Extract eligibility URL from current URL if possible
                if "eligibility" in current_url.lower() or "loadApp" in current_url.lower():
                    logger.info("No reset button found, reloading eligibility page...")
                    try:
                        # Switch to default content before reload
                        self.driver.switch_to.default_content()
                        
                        # Navigate to eligibility URL (try to go back to form)
                        # Use the full eligibility URL
                        eligibility_url = "https://essentials.availity.com/static/web/onb/onboarding-ui-apps/navigation/#/loadApp/?appUrl=%2Fstatic%2Fweb%2Fpres%2Fweb%2Feligibility%2F"
                        
                        logger.info(f"Reloading eligibility page: {eligibility_url}")
                        self.driver.get(eligibility_url)
                        
                        # Wait for page to fully load (increased wait)
                        logger.info("Waiting for page to fully load...")
                        time.sleep(10)  # Increased wait time for React app to load completely
                        
                        # Verify iframe and form are loaded
                        iframes = self.driver.find_elements(ByLocator.TAG_NAME, "iframe")
                        if iframes:
                            logger.info("Checking if form is loaded in iframe...")
                            try:
                                self.driver.switch_to.frame(iframes[0])
                                # Wait for payer field to be present (confirms form is loaded)
                                if self.exists((ByLocator.ID, "payerId"), timeout=5):
                                    logger.info("Page reloaded successfully - payer field is ready")
                                else:
                                    logger.warning("Payer field not found after reload, but continuing...")
                                self.driver.switch_to.default_content()
                            except:
                                self.driver.switch_to.default_content()
                        
                        logger.info("Page reload complete")
                        return
                    except Exception as e:
                        logger.warning(f"Could not reload page: {e}")
                
                logger.warning("Could not find reset button or reload page - form may need manual reset")
            else:
                logger.debug("Not on results page, form reset not needed")
            
        except Exception as e:
            logger.warning(f"Form reset failed: {e}, will continue and try to load form anyway...")

    def ensure_loaded(self) -> None:
        """
        Ensure the eligibility form is loaded.

        Raises:
            PortalChangedError: If form elements not found
        """
        try:
            # Wait for React app to fully load
            logger.info("Waiting for eligibility form to load...")
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
                # Wait a bit for iframe content to load
                time.sleep(2)
            
            # Wait for form elements to appear (use smart wait instead of fixed sleep)
            logger.debug("Looking for form elements...")
            
            # Try multiple approaches to find the form (reduced attempts and timeouts)
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    logger.debug(f"Attempt {attempt + 1}/{max_attempts} to find payer dropdown...")
                    # Try by ID first with shorter timeout
                    try:
                        # Re-find iframes if needed (to avoid stale element)
                        try:
                            self.driver.switch_to.default_content()
                            iframes = self.driver.find_elements(ByLocator.TAG_NAME, "iframe")
                            if iframes:
                                self.driver.switch_to.frame(iframes[0])
                                time.sleep(1)
                        except:
                            pass
                        
                        self.wait_for_visible((ByLocator.ID, "payerId"), timeout=5)
                        logger.info("Found payer dropdown by ID!")
                        break
                    except:
                        # Try by name
                        try:
                            self.wait_for_visible((ByLocator.NAME, "payerId"), timeout=3)
                            logger.info("Found payer dropdown by name!")
                            break
                        except:
                            # Try by CSS with different patterns
                            self.wait_for_visible((ByLocator.CSS_SELECTOR, "input[id*='payer'], input[name*='payer']"), timeout=3)
                            logger.info("Found payer field by CSS!")
                            break
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
                                raise PortalChangedError(f"Eligibility form not found after {max_attempts} attempts. Current URL: {self.driver.current_url}")
                    else:
                        # Reduced wait between retries
                        logger.debug(f"Waiting 1 second before retry...")
                        time.sleep(1)  # Reduced from 3 seconds
            
            logger.info("Eligibility form loaded successfully!")

        except Exception as e:
            logger.error(f"Eligibility form not loaded. Current URL: {self.driver.current_url}")
            logger.error("Taking screenshot for debugging...")
            raise PortalChangedError(f"Eligibility form not loaded: {e}") from e


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

            # Get the payer dropdown input
            payer_input = self.wait_for_clickable(self.PAYER_DROPDOWN, timeout=8)
            
            # IMPORTANT: Clear any existing selection first (for subsequent requests)
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Clear the field completely using Ctrl+A and Delete
            payer_input.click()
            time.sleep(0.3)  # Brief pause to ensure field is focused
            payer_input.send_keys(Keys.CONTROL + "a")
            payer_input.send_keys(Keys.DELETE)
            time.sleep(0.3)  # Brief pause after clearing
            
            # Now click to open the dropdown
            payer_input.click()
            
            # Wait for dropdown to open using WebDriverWait instead of sleep
            try:
                WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                    lambda d: payer_input.get_attribute("aria-expanded") == "true"
                )
            except:
                # If aria-expanded check fails, just wait a brief moment
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
            
            # Just press Enter to select the first/best match
            # React Select auto-filters, so typing the payer name will show the best matches first
            payer_input.send_keys(Keys.ENTER)
            
            # Wait for selection to complete (dropdown closes)
            try:
                WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                    lambda d: payer_input.get_attribute("aria-expanded") != "true"
                )
            except:
                # If check fails, just wait a brief moment
                time.sleep(0.5)
            
            # Verify selection by checking the input value
            time.sleep(0.5)
            selected_value = payer_input.get_attribute("value")
            logger.info(f"Payer selected - field shows: {selected_value}")

        except Exception as e:
            raise PortalChangedError(f"Failed to select payer: {e}") from e

    def switch_to_multiple_patients_tab(self) -> None:
        """
        Switch to the Multiple Patients tab if not already selected.
        
        Raises:
            PortalChangedError: If tab switching fails
        """
        try:
            from selenium.webdriver.common.by import By as ByLocator
            
            # Check if already on Multiple Patients tab
            try:
                tab = self.driver.find_element(*self.MULTIPLE_PATIENTS_TAB)
                if "Mui-selected" in tab.get_attribute("class"):
                    logger.info("Already on Multiple Patients tab")
                    return
            except:
                pass
            
            # Click the Multiple Patients tab
            logger.info("Switching to Multiple Patients tab...")
            multiple_patients_tab = self.wait_for_clickable(self.MULTIPLE_PATIENTS_TAB, timeout=5)
            multiple_patients_tab.click()
            
            # Wait for tab to be selected
            time.sleep(0.5)
            logger.info("Switched to Multiple Patients tab successfully")
            
        except Exception as e:
            raise PortalChangedError(f"Failed to switch to Multiple Patients tab: {e}") from e

    def fill_multiple_patients_textarea(self, patients_data: list[dict]) -> None:
        """
        Fill the multiple patients textarea with patient data.
        
        Format: Each line should be: memberId|lastName|firstName|dob
        Example: AB123456789|DOE|JOHN|06/15/1987
        
        Args:
            patients_data: List of dicts with keys: member_id, patient_last_name, patient_first_name, dob
            
        Raises:
            PortalChangedError: If textarea not found or filling fails
        """
        try:
            logger.info(f"Filling multiple patients textarea with {len(patients_data)} patients")
            
            # Build the text content - one patient per line
            lines = []
            for patient in patients_data:
                member_id = patient.get("member_id", "")
                last_name = patient.get("patient_last_name", "")
                first_name = patient.get("patient_first_name", "")
                dob = patient.get("dob")
                
                # Format DOB as MM/DD/YYYY
                if dob:
                    if isinstance(dob, str):
                        # If it's already a string, try to parse and reformat
                        try:
                            from datetime import datetime
                            dob_obj = datetime.strptime(dob, "%Y-%m-%d").date()
                            dob_str = dob_obj.strftime("%m/%d/%Y")
                        except:
                            dob_str = dob
                    else:
                        dob_str = dob.strftime("%m/%d/%Y")
                else:
                    dob_str = ""
                
                # Format: memberId|lastName|firstName|dob
                line = f"{member_id},{last_name},{first_name},{dob_str}"
                lines.append(line)
            
            text_content = "\n".join(lines)
            logger.debug(f"Multiple patients text content:\n{text_content}")
            
            # Find and fill the textarea
            textarea = None
            try:
                textarea = self.wait_for_visible(self.MULTIPLE_PATIENTS_TEXTAREA, timeout=5)
            except:
                try:
                    textarea = self.wait_for_visible(self.MULTIPLE_PATIENTS_TEXTAREA_ALT, timeout=5)
                except:
                    raise PortalChangedError("Could not find multiple patients textarea")
            
            # Clear and fill the textarea
            from selenium.webdriver.common.keys import Keys
            textarea.clear()
            textarea.send_keys(text_content)
            
            logger.info(f"Successfully filled multiple patients textarea with {len(patients_data)} patients")
            
        except Exception as e:
            raise PortalChangedError(f"Failed to fill multiple patients textarea: {e}") from e

    def fill_request_form(self, request: EligibilityRequest, use_multiple_patients: bool = False, multiple_patients_data: Optional[list[dict]] = None) -> None:
        """
        Fill the eligibility request form.
        
        Can fill either single patient form or multiple patients textarea.
        
        Note: For multiple patients, format is: memberId|lastName|firstName|dob (one per line)

        Args:
            request: EligibilityRequest with form data (used for single patient or as first patient in multiple)
            use_multiple_patients: If True, use Multiple Patients tab instead of single patient form
            multiple_patients_data: List of patient dicts for multiple patients mode (if None, uses request as single entry)

        Raises:
            ValidationError: If required fields are missing
            PortalChangedError: If form elements not found
        """
        try:
            logger.info(f"Filling eligibility form for request ID: {request.request_id}")
            if use_multiple_patients:
                logger.info("Using Multiple Patients mode")

            # Select payer using React Select
            self.select_payer(request.payer_name)

            # Wait for form fields to appear after payer selection (smart wait instead of fixed sleep)
            logger.info("Waiting for form fields to appear after payer selection...")
            time.sleep(2)  # Wait for form to populate after payer selection
            
            # Fill Provider Name/Search field FIRST (if provided)
            # This is the main provider search field at the top
            if request.provider_name:
                logger.info(f"Filling Provider Name: {request.provider_name}")
                try:
                    # Try to find provider search field
                    provider_search_input = None
                    max_attempts = 3
                    for attempt in range(max_attempts):
                        try:
                            # Try multiple selectors for provider search field
                            if self.exists(self.PROVIDER_SEARCH_DROPDOWN, timeout=3):
                                provider_search_input = self.wait_for_clickable(self.PROVIDER_SEARCH_DROPDOWN, timeout=3)
                                logger.info("Found Provider search field!")
                                break
                        except:
                            if attempt < max_attempts - 1:
                                time.sleep(0.5)
                            else:
                                logger.warning("Provider search field not found, will try Provider NPI instead")
                    
                    if provider_search_input:
                        # Fill provider name using React Select pattern
                        from selenium.webdriver.common.keys import Keys
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        
                        # Clear and type provider name
                        provider_search_input.click()
                        time.sleep(0.3)
                        provider_search_input.send_keys(Keys.CONTROL + "a")
                        provider_search_input.send_keys(Keys.DELETE)
                        time.sleep(0.3)
                        
                        # Type provider name
                        provider_search_input.send_keys(request.provider_name)
                        
                        # Wait for dropdown options
                        try:
                            WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='option'], [id*='option']"))
                            )
                        except:
                            time.sleep(0.5)
                        
                        # Press Enter to select
                        provider_search_input.send_keys(Keys.ENTER)
                        
                        # Wait for selection to complete
                        try:
                            WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                                lambda d: provider_search_input.get_attribute("aria-expanded") != "true"
                            )
                        except:
                            time.sleep(0.5)
                        
                        logger.info(f"Provider Name filled successfully: {request.provider_name}")
                        time.sleep(1)  # Wait for provider fields to populate
                except Exception as e:
                    logger.warning(f"Could not fill Provider Name: {e}, will try Provider NPI instead")
            
            # Provider NPI - Fill after provider name (or if provider name not provided)
            # The form requires one of: Provider NPI, Provider Tax ID, or Payer Assigned Provider ID
            logger.info("Filling Provider Information (Provider NPI)...")
            
            provider_filled = False
            try:
                # Try multiple times to find the NPI field
                npi_input = None
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        logger.debug(f"Attempt {attempt + 1} to find Provider NPI field...")
                        npi_input = self.wait_for_visible(self.PROVIDER_NPI_INPUT, timeout=5)
                        logger.info("Found Provider NPI field!")
                        break
                    except Exception as e:
                        if attempt < max_attempts - 1:
                            logger.debug(f"NPI field not found yet, retrying...")
                            time.sleep(0.5)
                        else:
                            raise
                
                if npi_input:
                    # Fill the NPI field if provided
                    if request.provider_npi:
                        logger.info(f"Filling Provider NPI: {request.provider_npi}")
                        npi_input.clear()
                        time.sleep(0.3)
                        npi_input.send_keys(request.provider_npi)
                        time.sleep(0.5)  # Wait for validation
                        logger.info(f"Provider NPI filled successfully: {request.provider_npi}")
                        provider_filled = True
                    else:
                        logger.warning("No Provider NPI provided - form may require Provider NPI, Tax ID, or Payer Assigned Provider ID")
                else:
                    logger.warning("Provider NPI field not found after all attempts")
            except Exception as e:
                logger.error(f"Could not fill provider NPI: {e}")
                raise PortalChangedError(f"Provider NPI field is required but could not be filled: {e}") from e
            
            # Wait a moment for provider information to be validated
            if provider_filled:
                time.sleep(1)  # Allow form to validate provider info
                logger.info("Provider information filled and validated")
            
            # Fill Patient Search Option (if field exists)
            # This field determines how to search for patients (e.g., "Member ID", "Name", etc.)
            try:
                if self.exists(self.PATIENT_SEARCH_OPTION, timeout=3):
                    logger.info("Filling Patient Search Option...")
                    # Try to select a common option like "Member ID" or "Name"
                    # The exact value depends on what options are available in the portal
                    patient_search_input = self.wait_for_clickable(self.PATIENT_SEARCH_OPTION, timeout=3)
                    
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    
                    # Click to open dropdown
                    patient_search_input.click()
                    time.sleep(0.3)
                    
                    # Wait for dropdown to open
                    try:
                        WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                            lambda d: patient_search_input.get_attribute("aria-expanded") == "true"
                        )
                    except:
                        time.sleep(0.5)
                    
                    # Try common options - start with "Member ID" as it's most common
                    search_options = ["Member ID", "MemberId", "memberId", "Name", "name", "Patient Name"]
                    option_selected = False
                    
                    for option in search_options:
                        try:
                            # Clear and type option
                            patient_search_input.send_keys(Keys.CONTROL + "a")
                            patient_search_input.send_keys(Keys.DELETE)
                            patient_search_input.send_keys(option)
                            
                            # Wait for options to appear
                            try:
                                WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='option'], [id*='option']"))
                                )
                            except:
                                time.sleep(0.3)
                            
                            # Press Enter to select
                            patient_search_input.send_keys(Keys.ENTER)
                            
                            # Wait for selection to complete
                            try:
                                WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                                    lambda d: patient_search_input.get_attribute("aria-expanded") != "true"
                                )
                            except:
                                time.sleep(0.3)
                            
                            logger.info(f"Selected Patient Search Option: {option}")
                            option_selected = True
                            break
                        except:
                            continue
                    
                    if not option_selected:
                        logger.warning("Could not select Patient Search Option, continuing...")
                else:
                    logger.debug("Patient Search Option field not found, skipping...")
            except Exception as e:
                logger.warning(f"Could not fill Patient Search Option: {e}, continuing...")
            
            # Switch to Multiple Patients tab if needed (after provider details)
            if use_multiple_patients:
                self.switch_to_multiple_patients_tab()
                time.sleep(1)  # Wait for tab content to load
            
            # Fill either multiple patients or single patient form
            if use_multiple_patients:
                # Fill multiple patients textarea
                if multiple_patients_data:
                    self.fill_multiple_patients_textarea(multiple_patients_data)
                else:
                    # Use request as single entry in multiple patients format
                    patient_data = {
                        "member_id": request.member_id,
                        "patient_last_name": request.patient_last_name,
                        "patient_first_name": request.patient_first_name or "",
                        "dob": request.dob,
                    }
                    self.fill_multiple_patients_textarea([patient_data])
            else:
                # Fill single patient fields with retries
                # Member ID
                max_retries = 2  # Reduced from 3
                for attempt in range(max_retries):
                    try:
                        self.wait_for_visible(self.MEMBER_ID_INPUT, timeout=5)  # Reduced from 8
                        break
                    except:
                        if attempt < max_retries - 1:
                            logger.debug(f"Waiting for member ID field, attempt {attempt + 1}...")
                            time.sleep(1)  # Reduced from 3
                        else:
                            raise
                
                self.type(self.MEMBER_ID_INPUT, request.member_id, clear_first=True)
                logger.debug(f"Member ID: {request.member_id}")
                
                # Patient last name (skip if field doesn't exist)
                try:
                    if self.exists(self.PATIENT_LAST_NAME_INPUT, timeout=2):  # Reduced from 3
                        self.type(self.PATIENT_LAST_NAME_INPUT, request.patient_last_name, clear_first=True)
                        logger.debug(f"Last name: {request.patient_last_name}")
                    else:
                        logger.debug("Patient last name field not found, skipping...")
                except Exception as e:
                    logger.warning(f"Could not fill patient last name: {e}, continuing...")
                
                # Patient first name (skip if field doesn't exist or not provided)
                if request.patient_first_name:
                    try:
                        if self.exists(self.PATIENT_FIRST_NAME_INPUT, timeout=2):  # Reduced from 3
                            self.type(self.PATIENT_FIRST_NAME_INPUT, request.patient_first_name, clear_first=True)
                            logger.debug(f"First name: {request.patient_first_name}")
                        else:
                            logger.debug("Patient first name field not found, skipping...")
                    except Exception as e:
                        logger.warning(f"Could not fill patient first name: {e}, continuing...")
                
                # Patient date of birth (skip if field doesn't exist)
                try:
                    if self.exists(self.PATIENT_DOB_INPUT, timeout=2):  # Reduced from 3
                        dob_str = request.dob.strftime("%m/%d/%Y")
                        self.type(self.PATIENT_DOB_INPUT, dob_str, clear_first=True)
                        logger.debug(f"Date of birth: {dob_str}")
                    else:
                        logger.debug("Patient DOB field not found, skipping...")
                except Exception as e:
                    logger.warning(f"Could not fill patient DOB: {e}, continuing...")
                
                # Click checkbox to submit another patient (if needed)
                try:
                    checkbox = self.wait_for_clickable(self.SUBMIT_ANOTHER_PATIENT_CHECKBOX, timeout=5)
                    if not checkbox.is_selected():
                        checkbox.click()
                        logger.debug("Checked 'Submit another patient' checkbox")
                except Exception as e:
                    logger.warning(f"Could not find/click submit another patient checkbox: {e}")

            # As of Date (single date field, not a range) - skip if doesn't exist
            try:
                if self.exists(self.DATE_OF_SERVICE, timeout=3):  # Reduced from 5
                    from selenium.webdriver.common.keys import Keys
                    # Use only dos_from (single date, not a range)
                    dos_str = request.dos_from.strftime("%m/%d/%Y")
                    # Get the input element and clear it properly
                    date_input = self.wait_for_visible(self.DATE_OF_SERVICE, timeout=3)  # Reduced from 5
                    # Clear existing value (select all and delete)
                    date_input.send_keys(Keys.CONTROL + "a")
                    date_input.send_keys(Keys.DELETE)
                    # Type the new date ONCE
                    date_input.send_keys(dos_str)
                    logger.debug(f"As of Date: {dos_str}")
                else:
                    logger.debug("As of Date field not found, skipping...")
            except Exception as e:
                logger.warning(f"Could not fill As of Date: {e}, continuing...")

            # Service type (if provided) - React Select (skip if doesn't exist)
            if request.service_type_code:
                try:
                    if self.exists(self.SERVICE_TYPE_DROPDOWN, timeout=3):
                        from selenium.webdriver.common.keys import Keys
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        service_input = self.wait_for_clickable(self.SERVICE_TYPE_DROPDOWN, timeout=3)
                        
                        # Click to open dropdown
                        service_input.click()
                        time.sleep(0.3)
                        
                        # Wait for dropdown to open
                        try:
                            WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                                lambda d: service_input.get_attribute("aria-expanded") == "true"
                            )
                        except:
                            time.sleep(0.5)
                        
                        # Clear existing value completely
                        service_input.send_keys(Keys.CONTROL + "a")
                        service_input.send_keys(Keys.DELETE)
                        time.sleep(0.3)
                        
                        # Type the service type code - be precise to avoid matching "15" when typing "1"
                        # Type character by character with small delay to ensure exact match
                        service_code_str = str(request.service_type_code)
                        logger.info(f"Filling Service Type Code: {service_code_str}")
                        
                        for char in service_code_str:
                            service_input.send_keys(char)
                            time.sleep(0.1)  # Small delay between characters
                        
                        # Wait a moment for options to filter
                        time.sleep(0.5)
                        
                        # Wait for dropdown options to appear
                        try:
                            WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='option'], [id*='option']"))
                            )
                        except:
                            time.sleep(0.3)
                        
                        # Press Enter to select the exact match
                        service_input.send_keys(Keys.ENTER)
                        
                        # Wait for selection to complete
                        try:
                            WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                                lambda d: service_input.get_attribute("aria-expanded") != "true"
                            )
                        except:
                            time.sleep(0.5)
                        
                        # Verify the selected value
                        selected_value = service_input.get_attribute("value")
                        logger.info(f"Service type code selected - field shows: {selected_value}")
                        
                        # If the selected value doesn't match, try to clear and retry with exact match
                        if selected_value and service_code_str not in selected_value:
                            logger.warning(f"Service type mismatch: expected '{service_code_str}', got '{selected_value}'. Retrying...")
                            # Clear and try again with exact code
                            service_input.click()
                            time.sleep(0.2)
                            service_input.send_keys(Keys.CONTROL + "a")
                            service_input.send_keys(Keys.DELETE)
                            time.sleep(0.2)
                            # Type the exact code
                            service_input.send_keys(service_code_str)
                            time.sleep(0.5)
                            # Look for exact match in dropdown options
                            try:
                                # Try to find and click the exact option
                                options = self.driver.find_elements(By.CSS_SELECTOR, "[class*='option'], [id*='option']")
                                for option in options:
                                    option_text = option.text.strip()
                                    if service_code_str in option_text or option_text.startswith(service_code_str):
                                        option.click()
                                        logger.info(f"Clicked exact service type option: {option_text}")
                                        break
                                else:
                                    # If no exact match found, press Enter
                                    service_input.send_keys(Keys.ENTER)
                            except:
                                service_input.send_keys(Keys.ENTER)
                            time.sleep(0.5)
                    else:
                        logger.debug("Service type field not found, skipping...")
                except Exception as e:
                    logger.warning(f"Could not fill service type: {e}, continuing...")
            logger.info("Form filled successfully")

        except Exception as e:
            logger.error(f"Failed to fill form: {e}")
            raise PortalChangedError(f"Form filling failed: {e}") from e

    def submit(self) -> None:
        """
        Submit the eligibility request form.

        Raises:
            PortalChangedError: If submit fails
        """
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            logger.info("Submitting eligibility request")
            
            # Wait for submit button to be visible and clickable
            submit_button = self.wait_for_clickable(self.SUBMIT_BUTTON, timeout=8)  # Reduced from 10
            
            # Wait until button is enabled (not disabled) with shorter polling
            wait = WebDriverWait(self.driver, 5, poll_frequency=0.2)  # Reduced from 10
            wait.until(lambda d: submit_button.is_enabled())
            
            # Scroll into view to ensure button is visible
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button)
            
            # Try regular click first
            try:
                submit_button.click()
                logger.debug("Submit button clicked")
            except Exception as e1:
                logger.warning(f"Regular click failed: {e1}, trying JavaScript click...")
                # Fallback to JavaScript click
                self.driver.execute_script("arguments[0].click();", submit_button)
                logger.debug("Submit button clicked via JavaScript")
            
            # Wait for form submission to start (check for loading indicator or page change)
            from selenium.webdriver.common.by import By as ByLocator
            current_url_before = self.driver.current_url
            try:
                WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                    lambda d: d.current_url != current_url_before or 
                             len(d.find_elements(ByLocator.CSS_SELECTOR, "[class*='loading'], [class*='spinner']")) > 0
                )
            except:
                # If wait fails, just proceed - form might have submitted successfully
                pass
            
            logger.info("Form submitted successfully")
            
        except Exception as e:
            raise PortalChangedError(f"Failed to submit form: {e}") from e

    def wait_for_results(self, timeout: int = 30) -> None:
        """
        Wait for eligibility results to load.

        Args:
            timeout: Maximum wait time in seconds

        Raises:
            PortalBusinessError: If portal returns a business error
            PortalChangedError: If results don't load
        """
        try:
            logger.info("Waiting for eligibility results")

            # Check for error messages first
            if self.exists(self.ERROR_MESSAGE, timeout=5):
                error_text = self.get_text(self.ERROR_MESSAGE)
                logger.warning(f"Portal returned error: {error_text}")
                raise PortalBusinessError(f"Portal error: {error_text}")

            # Wait for results container or patient history sidebar
            try:
                self.wait_for_visible(self.RESULTS_CONTAINER, timeout=timeout)
                logger.info("Results container loaded")
            except:
                # If results container not found, check for patient history sidebar
                try:
                    # Switch to default content to check sidebar
                    self.driver.switch_to.default_content()
                    # Wait a bit for sidebar to appear
                    time.sleep(3)
                    logger.info("Results container not found, checking for patient history...")
                except:
                    pass
            
            logger.info("Results loaded")

        except PortalBusinessError:
            raise
        except Exception as e:
            raise PortalChangedError(f"Results did not load: {e}") from e

    def check_and_click_patient_history(self) -> bool:
        """
        Check for patients in the history sidebar and click on the first one if found.
        
        Returns:
            True if a patient was found and clicked, False otherwise
        """
        try:
            logger.info("Checking for patient history sidebar...")
            
            # Switch to default content to access sidebar
            self.driver.switch_to.default_content()
            time.sleep(2)  # Wait for sidebar to load
            
            # Look for patient history items - try multiple selectors
            patient_selectors = [
                # Try to find patient items by text pattern (LASTNAME, FIRSTNAME)
                (By.XPATH, "//div[contains(@class, 'patient') or contains(@class, 'history')]//*[contains(text(), ',')]"),
                # Try to find clickable patient items
                (By.XPATH, "//div[contains(@class, 'patient')]//*[contains(text(), ',')]/ancestor::div[contains(@class, 'patient') or @role='button' or @onclick]"),
                # Try to find any div with patient-like text
                (By.XPATH, "//*[contains(text(), ',') and (contains(text(), 'Transaction Date') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'transaction'))]/ancestor::*[contains(@class, 'patient') or @role='button' or @onclick][1]"),
                # More generic - find any clickable element with patient name pattern
                (By.XPATH, "//*[contains(text(), ',') and string-length(normalize-space(text())) > 5]/ancestor::*[@role='button' or @onclick or contains(@class, 'clickable')][1]"),
            ]
            
            patient_element = None
            for selector in patient_selectors:
                try:
                    elements = self.driver.find_elements(*selector)
                    if elements:
                        # Find the first element that looks like a patient name (contains comma)
                        for elem in elements:
                            text = elem.text.strip()
                            if ',' in text and len(text) > 5:
                                # Check if it's clickable or find parent clickable element
                                try:
                                    # Try clicking the element itself
                                    if elem.is_displayed() and elem.is_enabled():
                                        patient_element = elem
                                        logger.info(f"Found patient in history: {text}")
                                        break
                                    # If not clickable, find parent
                                    parent = elem.find_element(By.XPATH, "./ancestor::*[@role='button' or @onclick or contains(@class, 'clickable')][1]")
                                    if parent:
                                        patient_element = parent
                                        logger.info(f"Found patient in history (parent): {text}")
                                        break
                                except:
                                    continue
                        if patient_element:
                            break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if patient_element:
                try:
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", patient_element)
                    time.sleep(0.5)
                    
                    # Try regular click first
                    try:
                        patient_element.click()
                        logger.info("Clicked on patient in history sidebar")
                    except:
                        # Fallback to JavaScript click
                        self.driver.execute_script("arguments[0].click();", patient_element)
                        logger.info("Clicked on patient in history sidebar (JavaScript)")
                    
                    # Wait for detailed results to load
                    time.sleep(3)
                    
                    # Switch back to iframe if needed
                    try:
                        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                        if iframes:
                            self.driver.switch_to.frame(iframes[0])
                            logger.info("Switched back to iframe after clicking patient")
                    except:
                        pass
                    
                    return True
                except Exception as e:
                    logger.warning(f"Failed to click patient in history: {e}")
                    return False
            else:
                logger.info("No patient found in history sidebar")
                # Switch back to iframe if we switched out
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    if iframes:
                        self.driver.switch_to.frame(iframes[0])
                except:
                    pass
                return False
                
        except Exception as e:
            logger.warning(f"Error checking patient history: {e}")
            # Switch back to iframe if we switched out
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    self.driver.switch_to.frame(iframes[0])
            except:
                pass
            return False

    def parse_summary(self) -> dict:
        """
        Parse summary information from results page.

        Returns:
            Dictionary with coverage_status, plan_name, plan_type, coverage_dates_str

        Raises:
            PortalChangedError: If parsing fails
        """
        try:
            summary = {}

            # Parse coverage status
            if self.exists(self.COVERAGE_STATUS, timeout=3):
                summary["coverage_status"] = self.get_text(self.COVERAGE_STATUS).strip()

            # Parse plan name
            if self.exists(self.PLAN_NAME, timeout=3):
                summary["plan_name"] = self.get_text(self.PLAN_NAME).strip()

            # Parse plan type
            if self.exists(self.PLAN_TYPE, timeout=3):
                summary["plan_type"] = self.get_text(self.PLAN_TYPE).strip()

            # Parse coverage dates
            if self.exists(self.COVERAGE_DATES, timeout=3):
                summary["coverage_dates_str"] = self.get_text(self.COVERAGE_DATES).strip()

            logger.debug(f"Parsed summary: {summary}")
            return summary

        except Exception as e:
            logger.warning(f"Failed to parse summary: {e}")
            return {}

    def parse_coverage_dates(self, dates_str: str) -> tuple[Optional[date], Optional[date]]:
        """
        Parse coverage dates from string.

        Expected format: "01/01/2025 - 12/31/2025" or similar.

        Args:
            dates_str: Date range string

        Returns:
            Tuple of (start_date, end_date)
        """
        try:
            # TODO: Adjust regex based on actual portal format
            match = re.search(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})", dates_str)
            if match:
                start_str, end_str = match.groups()
                start_date = datetime.strptime(start_str, "%m/%d/%Y").date()
                end_date = datetime.strptime(end_str, "%m/%d/%Y").date()
                return start_date, end_date
        except Exception as e:
            logger.warning(f"Failed to parse dates '{dates_str}': {e}")

        return None, None

    def parse_financial_field(self, locator: tuple[By, str]) -> Optional[float]:
        """
        Parse a financial field (handles $1,234.56 format).

        Args:
            locator: Element locator

        Returns:
            Float value or None
        """
        try:
            if self.exists(locator, timeout=2):
                text = self.get_text(locator).strip()
                # Remove $ and commas, parse as float
                cleaned = re.sub(r"[$,]", "", text)
                return float(cleaned)
        except Exception as e:
            logger.debug(f"Could not parse financial field {locator}: {e}")

        return None

    def parse_benefits_table(self) -> list[EligibilityBenefitLine]:
        """
        Parse benefits table into benefit lines.

        TODO: Implement based on actual table structure.

        Returns:
            List of EligibilityBenefitLine objects
        """
        benefit_lines = []

        try:
            if not self.exists(self.BENEFITS_TABLE, timeout=3):
                logger.warning("Benefits table not found")
                return benefit_lines

            rows = self.find_elements(self.BENEFITS_ROWS, timeout=5)
            logger.info(f"Found {len(rows)} benefit rows")

            # TODO: Parse each row based on actual table columns
            # Example structure (adjust to actual portal):
            # | Benefit Category | Network | Copay | Coinsurance | Deductible | Notes |

            for row in rows:
                try:
                    # TODO: Extract cell values based on column positions
                    # cells = row.find_elements(By.TAG_NAME, "td")
                    # benefit_category = cells[0].text.strip()
                    # network_tier = cells[1].text.strip()
                    # ... etc

                    # Placeholder benefit line
                    benefit_line = EligibilityBenefitLine(
                        benefit_category="Placeholder Benefit",
                        service_type_code=None,
                        network_tier=None,
                        copay_amount=None,
                        coinsurance_percent=None,
                        deductible_amount=None,
                        max_benefit_amount=None,
                        notes="TODO: Parse from actual table",
                    )
                    benefit_lines.append(benefit_line)

                except Exception as e:
                    logger.warning(f"Failed to parse benefit row: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to parse benefits table: {e}")

        return benefit_lines

    def _extract_text_by_label(self, label_text: str, timeout: int = 3) -> Optional[str]:
        """
        Extract text value by finding a label and getting the associated value.
        
        Args:
            label_text: The label text to search for (e.g., "Member Status", "Date of Birth")
            timeout: Maximum wait time in seconds
            
        Returns:
            The value text or None if not found
        """
        try:
            # Strategy 1: Find label and get next sibling or following text
            xpath_patterns = [
                # Label followed by value in same element or next sibling
                f"//*[contains(text(), '{label_text}')]/following-sibling::*[1]",
                f"//*[contains(text(), '{label_text}')]/../following-sibling::*[1]",
                # Label with value in parent's next sibling
                f"//*[contains(text(), '{label_text}')]/ancestor::*[1]/following-sibling::*[1]",
                # Find by label and get text after colon
                f"//*[contains(text(), '{label_text}')]",
            ]
            
            for xpath in xpath_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for elem in elements:
                        text = elem.text.strip()
                        if label_text in text:
                            # Extract value after label (e.g., "Date of Birth: Jun 22, 2025")
                            if ':' in text:
                                parts = text.split(':', 1)
                                if len(parts) > 1:
                                    value = parts[1].strip()
                                    if value:
                                        logger.debug(f"Extracted {label_text}: {value}")
                                        return value
                            # If no colon, try to get next sibling text
                            try:
                                next_sibling = elem.find_element(By.XPATH, "./following-sibling::*[1]")
                                value = next_sibling.text.strip()
                                if value:
                                    logger.debug(f"Extracted {label_text} (sibling): {value}")
                                    return value
                            except:
                                pass
                except:
                    continue
            
            # Strategy 2: Look for the value near the label using regex-like patterns
            try:
                # Get all text on page and search for pattern
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                import re
                # Pattern: "Label: Value" or "Label Value"
                pattern = rf"{re.escape(label_text)}[:\s]+([^\n\r]+)"
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value:
                        logger.debug(f"Extracted {label_text} (regex): {value}")
                        return value
            except:
                pass
            
            return None
        except Exception as e:
            logger.debug(f"Could not extract {label_text}: {e}")
            return None

    def parse_detailed_eligibility(self) -> dict:
        """
        Parse detailed eligibility information from the results page.
        
        Extracts fields like:
        - Member Status
        - Date of Birth
        - Gender
        - Relationship to Subscriber
        - Member ID
        - Subscriber Name
        - Group Number
        - Group Name
        - Plan Number
        - Plan Begin Date
        - Eligibility Begin Date
        - Payer Name
        
        Returns:
            Dictionary with extracted fields
        """
        detailed_data = {}
        
        try:
            logger.info("Parsing detailed eligibility information...")
            
            # Extract Member Status
            member_status = self._extract_text_by_label("Member Status")
            if member_status:
                detailed_data["member_status"] = member_status
            else:
                # Try direct selector
                try:
                    if self.exists(self.MEMBER_STATUS, timeout=2):
                        status_text = self.get_text(self.MEMBER_STATUS)
                        # Extract status from text like "Member Status: Active Coverage" or just "Active Coverage"
                        if ':' in status_text:
                            detailed_data["member_status"] = status_text.split(':', 1)[1].strip()
                        else:
                            detailed_data["member_status"] = status_text.strip()
                except:
                    pass
            
            # Extract Date of Birth
            dob_text = self._extract_text_by_label("Date of Birth")
            if dob_text:
                detailed_data["date_of_birth"] = dob_text
            
            # Extract Gender
            gender = self._extract_text_by_label("Gender")
            if gender:
                detailed_data["gender"] = gender
            
            # Extract Relationship to Subscriber
            relationship = self._extract_text_by_label("Relationship to Subscriber")
            if relationship:
                detailed_data["relationship_to_subscriber"] = relationship
            
            # Extract Member ID
            member_id = self._extract_text_by_label("Member ID")
            if member_id:
                detailed_data["member_id"] = member_id
            
            # Extract Subscriber Name
            subscriber = self._extract_text_by_label("Subscriber")
            if subscriber:
                detailed_data["subscriber_name"] = subscriber
            
            # Extract Group Number
            group_number = self._extract_text_by_label("Group Number")
            if group_number:
                detailed_data["group_number"] = group_number
            
            # Extract Group Name
            group_name = self._extract_text_by_label("Group Name")
            if group_name:
                detailed_data["group_name"] = group_name
            
            # Extract Plan Number
            plan_number = self._extract_text_by_label("Plan Number")
            if plan_number:
                detailed_data["plan_number"] = plan_number
            
            # Extract Plan Begin Date
            plan_begin = self._extract_text_by_label("Plan Begin Date")
            if plan_begin:
                detailed_data["plan_begin_date"] = plan_begin
            
            # Extract Eligibility Begin Date
            eligibility_begin = self._extract_text_by_label("Eligibility Begin Date")
            if eligibility_begin:
                detailed_data["eligibility_begin_date"] = eligibility_begin
            
            # Extract Payer Name
            payer = self._extract_text_by_label("Payer")
            if payer:
                detailed_data["payer_name"] = payer
            
            logger.info(f"Extracted detailed eligibility data: {len(detailed_data)} fields")
            logger.debug(f"Detailed data: {detailed_data}")
            
        except Exception as e:
            logger.warning(f"Error parsing detailed eligibility: {e}")
        
        return detailed_data

    def parse_result(self, request: EligibilityRequest) -> EligibilityResult:
        """
        Parse complete eligibility result from the page.

        Args:
            request: Original request

        Returns:
            EligibilityResult object
        """
        logger.info("Parsing eligibility results")

        # First, check for patient history and click if found
        patient_clicked = self.check_and_click_patient_history()
        if patient_clicked:
            logger.info("Patient clicked in history, waiting for detailed results...")
            time.sleep(2)  # Wait for detailed results to load
        
        # Parse detailed eligibility information (from detailed results page)
        detailed_data = self.parse_detailed_eligibility()

        # Parse summary
        summary = self.parse_summary()

        # Parse coverage dates
        coverage_dates_str = summary.get("coverage_dates_str", "")
        coverage_start_date, coverage_end_date = self.parse_coverage_dates(coverage_dates_str)

        # Parse financial fields
        deductible_individual = self.parse_financial_field(self.DEDUCTIBLE_INDIVIDUAL)
        deductible_remaining_individual = self.parse_financial_field(self.DEDUCTIBLE_REMAINING)
        oop_max_individual = self.parse_financial_field(self.OOP_MAX_INDIVIDUAL)
        oop_max_family = self.parse_financial_field(self.OOP_MAX_FAMILY)

        # Parse benefit lines
        benefit_lines = self.parse_benefits_table()

        # Use detailed data to populate result, with fallback to summary
        coverage_status = detailed_data.get("member_status") or summary.get("coverage_status")
        member_id = detailed_data.get("member_id") or request.member_id

        result = EligibilityResult(
            request_id=request.request_id,
            coverage_status=coverage_status,
            plan_name=summary.get("plan_name"),
            plan_type=summary.get("plan_type"),
            coverage_start_date=coverage_start_date,
            coverage_end_date=coverage_end_date,
            deductible_individual=deductible_individual,
            deductible_remaining_individual=deductible_remaining_individual,
            oop_max_individual=oop_max_individual,
            oop_max_family=oop_max_family,
            benefit_lines=benefit_lines,
            raw_response_html_path=None,  # Will be set by bot if saving HTML
            # Detailed eligibility fields
            member_status=detailed_data.get("member_status"),
            date_of_birth=detailed_data.get("date_of_birth"),
            gender=detailed_data.get("gender"),
            relationship_to_subscriber=detailed_data.get("relationship_to_subscriber"),
            member_id_result=member_id,
            subscriber_name=detailed_data.get("subscriber_name"),
            group_number=detailed_data.get("group_number"),
            group_name=detailed_data.get("group_name"),
            plan_number=detailed_data.get("plan_number"),
            plan_begin_date=detailed_data.get("plan_begin_date"),
            eligibility_begin_date=detailed_data.get("eligibility_begin_date"),
            payer_name_result=detailed_data.get("payer_name"),
        )

        logger.info(f"Parsed result for request {request.request_id}")
        return result

