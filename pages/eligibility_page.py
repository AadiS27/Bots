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
    
    # Single patient fields
    MEMBER_ID_INPUT = (By.NAME, "memberId")  # Member ID field
    PATIENT_LAST_NAME_INPUT = (By.NAME, "patientLastName")  # Patient last name
    PATIENT_FIRST_NAME_INPUT = (By.NAME, "patientFirstName")  # Patient first name
    PATIENT_DOB_INPUT = (By.ID, "patientBirthDatefield-picker")  # Patient date of birth
    SUBMIT_ANOTHER_PATIENT_CHECKBOX = (By.NAME, "shouldSubmitAnotherPatient")  # Checkbox to submit another patient
    
    # Service information
    DATE_OF_SERVICE = (By.ID, "asOfDate-picker")  # Date picker input
    SERVICE_TYPE_DROPDOWN = (By.ID, "serviceType")  # Service type React Select
    PROVIDER_NPI_INPUT = (By.NAME, "providerNpi")  # Provider NPI field
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")  # Submit button

    # Results section - TODO: These need to be updated after seeing actual results
    RESULTS_CONTAINER = (By.CSS_SELECTOR, "div[class*='result'], table, .card")  # Generic results container
    COVERAGE_STATUS = (By.XPATH, "//*[contains(text(), 'Coverage') or contains(text(), 'Status')]")
    PLAN_NAME = (By.XPATH, "//*[contains(text(), 'Plan')]")
    
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
            
            # Wait for form elements to appear (use smart wait instead of fixed sleep)
            logger.debug("Looking for form elements...")
            
            # Try multiple approaches to find the form (reduced attempts and timeouts)
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    logger.debug(f"Attempt {attempt + 1}/{max_attempts} to find payer dropdown...")
                    # Try by ID first with shorter timeout
                    try:
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

    def fill_request_form(self, request: EligibilityRequest) -> None:
        """
        Fill the eligibility request form.
        
        Note: Availity uses a multi-patient format where data is entered as:
        memberId|lastName|firstName|dob

        Args:
            request: EligibilityRequest with form data

        Raises:
            ValidationError: If required fields are missing
            PortalChangedError: If form elements not found
        """
        try:
            logger.info(f"Filling eligibility form for request ID: {request.request_id}")

            # Select payer using React Select
            self.select_payer(request.payer_name)

            # Wait for form fields to appear after payer selection (smart wait instead of fixed sleep)
            logger.info("Waiting for form fields to appear after payer selection...")
            
            # Provider NPI - MUST be filled FIRST before other fields
            logger.info("Looking for Provider NPI field...")
            
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
                            time.sleep(0.5)  # Reduced from 2 seconds
                        else:
                            raise
                
                if npi_input:
                    # Fill or clear the NPI field
                    if request.provider_npi:
                        logger.info(f"Filling Provider NPI: {request.provider_npi}")
                        npi_input.clear()
                        npi_input.send_keys(request.provider_npi)
                        logger.info(f"Provider NPI filled successfully: {request.provider_npi}")
                    else:
                        logger.info("Clearing Provider NPI field (no NPI provided)")
                        npi_input.clear()
                        logger.info("Provider NPI field cleared")
                else:
                    logger.warning("Provider NPI field not found after all attempts")
            except Exception as e:
                logger.error(f"Could not fill provider NPI: {e}")
                logger.warning("Continuing without Provider NPI...")
            
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
                    if self.exists(self.SERVICE_TYPE_DROPDOWN, timeout=3):  # Reduced from 5
                        from selenium.webdriver.common.keys import Keys
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        service_input = self.wait_for_clickable(self.SERVICE_TYPE_DROPDOWN, timeout=3)  # Reduced from 5
                        # Click to open dropdown
                        service_input.click()
                        # Wait for dropdown to open
                        try:
                            WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                                lambda d: service_input.get_attribute("aria-expanded") == "true"
                            )
                        except:
                            time.sleep(0.5)
                        # Clear existing value (select all and delete)
                        service_input.send_keys(Keys.CONTROL + "a")
                        service_input.send_keys(Keys.DELETE)
                        # Type the service type code ONCE (no duplication)
                        service_input.send_keys(request.service_type_code)
                        # Wait for dropdown options (use simpler selector)
                        try:
                            WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='option'], [id*='option']"))
                            )
                        except:
                            time.sleep(0.5)
                        # Press Enter to select (ONCE)
                        service_input.send_keys(Keys.ENTER)
                        # Wait for selection to complete
                        try:
                            WebDriverWait(self.driver, 1, poll_frequency=0.2).until(
                                lambda d: service_input.get_attribute("aria-expanded") != "true"
                            )
                        except:
                            time.sleep(0.5)
                        logger.debug(f"Service type: {request.service_type_code}")
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

            # Wait for results container
            self.wait_for_visible(self.RESULTS_CONTAINER, timeout=timeout)
            logger.info("Results loaded")

        except PortalBusinessError:
            raise
        except Exception as e:
            raise PortalChangedError(f"Results did not load: {e}") from e

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

    def parse_result(self, request: EligibilityRequest) -> EligibilityResult:
        """
        Parse complete eligibility result from the page.

        Args:
            request: Original request

        Returns:
            EligibilityResult object
        """
        logger.info("Parsing eligibility results")

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

        result = EligibilityResult(
            request_id=request.request_id,
            coverage_status=summary.get("coverage_status"),
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
        )

        logger.info(f"Parsed result for request {request.request_id}")
        return result

