"""Claims submission page object for form filling and result parsing."""

import time
from typing import Optional

from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.errors import PortalBusinessError, PortalChangedError, ValidationError
from domain.claims_models import ClaimsQuery, ClaimsResult, ServiceLine

from .base_page import BasePage


class ClaimsPage(BasePage):
    """Page object for Availity claims submission form and results."""

    # Form fields - MUI Autocomplete components
    TRANSACTION_TYPE_INPUT = (By.NAME, "transactionType")  # Claim type autocomplete
    PAYER_INPUT = (By.NAME, "payer")  # Payer autocomplete (may be disabled initially)
    RESPONSIBILITY_SEQUENCE_INPUT = (By.NAME, "responsibilitySequence")  # Responsibility sequence autocomplete

    # Patient information fields
    PATIENT_LAST_NAME_INPUT = (By.NAME, "patient.lastName")
    PATIENT_FIRST_NAME_INPUT = (By.NAME, "patient.firstName")
    PATIENT_BIRTH_DATE_INPUT = (By.NAME, "patient.birthDate")
    PATIENT_GENDER_CODE_INPUT = (By.NAME, "patient.genderCode")  # Autocomplete
    PATIENT_SUBSCRIBER_RELATIONSHIP_CODE_INPUT = (By.NAME, "patient.subscriberRelationshipCode")  # Autocomplete

    # Patient address fields
    PATIENT_ADDRESS_LINE1_INPUT = (By.NAME, "patient.addressLine1")
    PATIENT_COUNTRY_CODE_INPUT = (By.NAME, "patient.countryCode")  # Autocomplete
    PATIENT_CITY_INPUT = (By.NAME, "patient.city")
    PATIENT_STATE_CODE_INPUT = (By.NAME, "patient.stateCode")  # Autocomplete
    PATIENT_ZIP_CODE_INPUT = (By.NAME, "patient.zipCode")

    # Subscriber information fields
    SUBSCRIBER_MEMBER_ID_INPUT = (By.NAME, "subscriber.memberId")
    SUBSCRIBER_GROUP_NUMBER_INPUT = (By.NAME, "subscriber.groupNumber")

    # Claim information fields
    PATIENT_PAID_AMOUNT_INPUT = (By.NAME, "claimInformation.patientPaidAmount")
    BENEFITS_ASSIGNMENT_CERTIFICATION_INPUT = (By.NAME, "claimInformation.benefitsAssignmentCertification")  # Autocomplete
    CLAIM_CONTROL_NUMBER_INPUT = (By.NAME, "claimInformation.controlNumber")
    PLACE_OF_SERVICE_CODE_INPUT = (By.NAME, "claimInformation.placeOfServiceCode")  # Autocomplete
    FREQUENCY_TYPE_CODE_INPUT = (By.NAME, "claimInformation.frequencyTypeCode")  # Autocomplete
    PROVIDER_ACCEPT_ASSIGNMENT_CODE_INPUT = (By.NAME, "claimInformation.providerAcceptAssignmentCode")  # Autocomplete
    INFORMATION_RELEASE_CODE_INPUT = (By.NAME, "claimInformation.informationReleaseCode")  # Autocomplete
    PROVIDER_SIGNATURE_ON_FILE_INPUT = (By.NAME, "claimInformation.providerSignatureOnFile")  # Autocomplete
    PAYER_CLAIM_FILING_INDICATOR_CODE_INPUT = (By.NAME, "payer.claimFilingIndicatorCode")  # Autocomplete
    MEDICAL_RECORD_NUMBER_INPUT = (By.NAME, "claimInformation.medicalRecordNumber")

    # Billing provider information fields
    BILLING_PROVIDER_LAST_NAME_INPUT = (By.NAME, "billingProvider.lastName")
    BILLING_PROVIDER_FIRST_NAME_INPUT = (By.NAME, "billingProvider.firstName")
    BILLING_PROVIDER_NPI_INPUT = (By.NAME, "billingProvider.npi")
    BILLING_PROVIDER_TAX_ID_EIN_INPUT = (By.NAME, "billingProvider.taxId.ein")
    BILLING_PROVIDER_TAX_ID_SSN_INPUT = (By.NAME, "billingProvider.taxId.ssn")
    BILLING_PROVIDER_SPECIALTY_CODE_INPUT = (By.NAME, "billingProvider.specialtyCode")  # Autocomplete
    BILLING_PROVIDER_ADDRESS_LINE1_INPUT = (By.NAME, "billingProvider.addressLine1")
    BILLING_PROVIDER_COUNTRY_CODE_INPUT = (By.NAME, "billingProvider.countryCode")  # Autocomplete
    BILLING_PROVIDER_CITY_INPUT = (By.NAME, "billingProvider.city")
    BILLING_PROVIDER_STATE_CODE_INPUT = (By.NAME, "billingProvider.stateCode")  # Autocomplete
    BILLING_PROVIDER_ZIP_CODE_INPUT = (By.NAME, "billingProvider.zipCode")

    # Diagnosis fields
    DIAGNOSIS_CODE_INPUT = (By.NAME, "claimInformation.diagnoses.0.code")  # Autocomplete

    # Service line fields (for index 0, will be dynamic for multiple lines)
    SERVICE_LINE_FROM_DATE_INPUT = (By.NAME, "claimInformation.serviceLines.0.fromDate")
    SERVICE_LINE_PLACE_OF_SERVICE_CODE_INPUT = (By.NAME, "claimInformation.serviceLines.0.placeOfServiceCode")  # Autocomplete
    SERVICE_LINE_PROCEDURE_CODE_INPUT = (By.NAME, "claimInformation.serviceLines.0.procedureCode")  # Autocomplete
    SERVICE_LINE_DIAGNOSIS_CODE_POINTER1_INPUT = (By.NAME, "claimInformation.serviceLines.0.diagnosisCodePointer1")  # Autocomplete
    SERVICE_LINE_AMOUNT_INPUT = (By.NAME, "claimInformation.serviceLines.0.amount")
    SERVICE_LINE_QUANTITY_INPUT = (By.NAME, "claimInformation.serviceLines.0.quantity")
    SERVICE_LINE_QUANTITY_TYPE_CODE_INPUT = (By.NAME, "claimInformation.serviceLines.0.quantityTypeCode")  # Autocomplete

    # Add service line button
    ADD_SERVICE_LINE_BUTTON = (By.XPATH, "//button[contains(., 'Add a Line')]")

    # Alternative selectors for dynamic IDs
    TRANSACTION_TYPE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='transactionType']")
    PAYER_INPUT_ALT = (By.CSS_SELECTOR, "input[name='payer']")
    RESPONSIBILITY_SEQUENCE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='responsibilitySequence']")
    PATIENT_GENDER_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='patient.genderCode']")
    PATIENT_SUBSCRIBER_RELATIONSHIP_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='patient.subscriberRelationshipCode']")
    PATIENT_COUNTRY_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='patient.countryCode']")
    PATIENT_STATE_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='patient.stateCode']")
    BENEFITS_ASSIGNMENT_CERTIFICATION_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.benefitsAssignmentCertification']")
    BILLING_PROVIDER_SPECIALTY_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='billingProvider.specialtyCode']")
    BILLING_PROVIDER_COUNTRY_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='billingProvider.countryCode']")
    BILLING_PROVIDER_STATE_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='billingProvider.stateCode']")
    PLACE_OF_SERVICE_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.placeOfServiceCode']")
    FREQUENCY_TYPE_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.frequencyTypeCode']")
    PROVIDER_ACCEPT_ASSIGNMENT_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.providerAcceptAssignmentCode']")
    INFORMATION_RELEASE_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.informationReleaseCode']")
    PROVIDER_SIGNATURE_ON_FILE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.providerSignatureOnFile']")
    PAYER_CLAIM_FILING_INDICATOR_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='payer.claimFilingIndicatorCode']")
    DIAGNOSIS_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.diagnoses.0.code']")
    SERVICE_LINE_PLACE_OF_SERVICE_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.serviceLines.0.placeOfServiceCode']")
    SERVICE_LINE_PROCEDURE_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.serviceLines.0.procedureCode']")
    SERVICE_LINE_DIAGNOSIS_CODE_POINTER1_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.serviceLines.0.diagnosisCodePointer1']")
    SERVICE_LINE_QUANTITY_TYPE_CODE_INPUT_ALT = (By.CSS_SELECTOR, "input[name='claimInformation.serviceLines.0.quantityTypeCode']")

    # Submit button - TODO: Update based on actual submit button selector
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "button[type='submit'], button[class*='submit']")
    SUBMIT_BUTTON_XPATH = (By.XPATH, "//button[contains(text(), 'Submit') or contains(., 'Submit')]")

    # Results section - TODO: Update based on actual results page structure
    RESULTS_CONTAINER = (By.CSS_SELECTOR, "div[class*='result'], div[class*='success'], div[class*='confirmation']")
    SUCCESS_MESSAGE = (By.CSS_SELECTOR, "[class*='success'], [class*='confirmation']")
    CLAIM_ID_TEXT = (By.XPATH, "//*[contains(text(), 'Claim ID') or contains(text(), 'Confirmation')]")

    # Error messages
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".error-message, .alert-danger, [role='alert'], [class*='error']")

    def __init__(self, driver: WebDriver):
        """
        Initialize claims page.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def ensure_loaded(self) -> None:
        """
        Ensure the claims submission form is loaded.

        Raises:
            PortalChangedError: If form elements not found
        """
        try:
            logger.info("Waiting for claims submission form to load...")
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
                    logger.debug(f"Attempt {attempt + 1}/{max_attempts} to find claims form...")
                    # Try to find transaction type input
                    try:
                        self.wait_for_presence(self.TRANSACTION_TYPE_INPUT, timeout=5)
                        logger.info("Found transaction type input by name!")
                        break
                    except:
                        # Try alternative selector
                        try:
                            self.wait_for_presence(self.TRANSACTION_TYPE_INPUT_ALT, timeout=3)
                            logger.info("Found transaction type input by CSS!")
                            break
                        except:
                            # Try responsibility sequence (should have default value)
                            try:
                                self.wait_for_presence(self.RESPONSIBILITY_SEQUENCE_INPUT, timeout=3)
                                logger.info("Found responsibility sequence input - form is loaded!")
                                break
                            except:
                                pass
                except Exception as e:
                    if attempt == max_attempts - 1:
                        # Last attempt - try to find ANY input field
                        try:
                            self.wait_for_presence((ByLocator.CSS_SELECTOR, "input, textarea"), timeout=3)
                            logger.info("Found some form input - form is loaded!")
                            break
                        except:
                            raise PortalChangedError(
                                f"Claims form not found after {max_attempts} attempts. Current URL: {self.driver.current_url}"
                            )
                    else:
                        logger.debug(f"Waiting 1 second before retry...")
                        time.sleep(1)

            logger.info("Claims submission form loaded successfully!")

        except Exception as e:
            logger.error(f"Claims form not loaded. Current URL: {self.driver.current_url}")
            logger.error("Taking screenshot for debugging...")
            raise PortalChangedError(f"Claims form not loaded: {e}") from e

    def select_autocomplete(self, locator: tuple[By, str], value: str, field_name: str) -> None:
        """
        Select a value from MUI Autocomplete field.

        Args:
            locator: Locator tuple for the autocomplete input
            value: Value to select
            field_name: Name of the field (for logging)

        Raises:
            PortalChangedError: If selection fails
        """
        try:
            logger.info(f"Selecting {field_name}: {value}")

            # Try to find the input field
            autocomplete_input = None
            try:
                autocomplete_input = self.wait_for_clickable(locator, timeout=5)
            except:
                # Try alternative selector
                if locator == self.TRANSACTION_TYPE_INPUT:
                    autocomplete_input = self.wait_for_clickable(self.TRANSACTION_TYPE_INPUT_ALT, timeout=5)
                elif locator == self.PAYER_INPUT:
                    autocomplete_input = self.wait_for_clickable(self.PAYER_INPUT_ALT, timeout=5)
                elif locator == self.RESPONSIBILITY_SEQUENCE_INPUT:
                    autocomplete_input = self.wait_for_clickable(self.RESPONSIBILITY_SEQUENCE_INPUT_ALT, timeout=5)

            if not autocomplete_input:
                raise PortalChangedError(f"Could not find {field_name} autocomplete input")

            # Check if field is disabled
            if not autocomplete_input.is_enabled():
                logger.warning(f"{field_name} field is disabled, skipping...")
                return

            # Wait for any backdrop/overlay to disappear
            try:
                WebDriverWait(self.driver, 3).until(
                    lambda d: d.execute_script("return document.querySelector('.MuiBackdrop-root') === null || window.getComputedStyle(document.querySelector('.MuiBackdrop-root')).opacity === '0'")
                )
            except:
                time.sleep(0.5)  # Fallback wait

            # Clear existing value completely - try multiple methods
            current_value = autocomplete_input.get_attribute("value")
            if current_value:
                logger.debug(f"Clearing existing value: {current_value}")
                # Method 1: Click and clear with keyboard
                try:
                    self.driver.execute_script("arguments[0].focus();", autocomplete_input)
                    time.sleep(0.2)
                    autocomplete_input.send_keys(Keys.CONTROL + "a")
                    time.sleep(0.2)
                    autocomplete_input.send_keys(Keys.DELETE)
                    time.sleep(0.2)
                    autocomplete_input.send_keys(Keys.BACKSPACE)
                    time.sleep(0.2)
                except:
                    pass
                
                # Method 2: Clear via JavaScript
                try:
                    self.driver.execute_script("arguments[0].value = '';", autocomplete_input)
                    # Trigger input event to notify React
                    self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", autocomplete_input)
                    time.sleep(0.2)
                except:
                    pass

            # Scroll into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", autocomplete_input)
            time.sleep(0.3)

            # Use JavaScript click to avoid backdrop interception
            self.driver.execute_script("arguments[0].click();", autocomplete_input)
            time.sleep(0.3)

            # Wait for dropdown to open
            try:
                WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                    lambda d: autocomplete_input.get_attribute("aria-expanded") == "true"
                )
            except:
                # Try clicking again if dropdown didn't open
                self.driver.execute_script("arguments[0].click();", autocomplete_input)
                time.sleep(0.5)

            # Type the value to search/filter (character by character for better reliability)
            autocomplete_input.clear()
            time.sleep(0.2)
            for char in value:
                autocomplete_input.send_keys(char)
                time.sleep(0.1)
            time.sleep(0.5)  # Wait for autocomplete to filter

            # Wait for results to appear
            try:
                WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[role='option'], [class*='option'], li[role='option'], ul[role='listbox'] li"))
                )
            except:
                time.sleep(0.5)

            # Try to find and click the exact option matching the value
            try:
                # Look for option that contains the value text
                option_xpath = f"//li[@role='option' and contains(., '{value}')]"
                option = self.driver.find_element(By.XPATH, option_xpath)
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", option)
                time.sleep(0.2)
                self.driver.execute_script("arguments[0].click();", option)
                logger.debug(f"Clicked option directly: {value}")
            except:
                # Fallback: Press Enter to select the first/best match
                autocomplete_input.send_keys(Keys.ENTER)
                logger.debug(f"Used Enter key to select: {value}")

            time.sleep(0.5)

            # Wait for selection to complete
            try:
                WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                    lambda d: autocomplete_input.get_attribute("aria-expanded") != "true" or autocomplete_input.get_attribute("aria-expanded") == "false"
                )
            except:
                time.sleep(0.5)

            # Verify selection (re-find element to avoid stale reference)
            try:
                autocomplete_input = self.wait_for_visible(locator, timeout=5)
                selected_value = autocomplete_input.get_attribute("value")
                if selected_value and value.lower() in selected_value.lower():
                    logger.info(f"{field_name} selected - field shows: {selected_value}")
                else:
                    logger.warning(f"{field_name} selection may not have worked. Expected: {value}, Got: {selected_value}")
            except Exception as verify_error:
                logger.warning(f"Could not verify {field_name} selection: {verify_error}")

        except Exception as e:
            # Check if it's a stale element error and retry once
            if "stale" in str(e).lower() or "not found in the current frame" in str(e):
                logger.warning(f"Stale element error for {field_name}, retrying once...")
                try:
                    time.sleep(1)
                    # Retry the entire selection process
                    autocomplete_input = self.wait_for_visible(locator, timeout=10)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", autocomplete_input)
                    time.sleep(0.3)
                    self.driver.execute_script("arguments[0].click();", autocomplete_input)
                    time.sleep(0.3)
                    autocomplete_input = self.wait_for_visible(locator, timeout=5)
                    autocomplete_input.clear()
                    time.sleep(0.2)
                    for char in value:
                        autocomplete_input.send_keys(char)
                        time.sleep(0.1)
                    time.sleep(0.5)
                    autocomplete_input.send_keys(Keys.ENTER)
                    time.sleep(0.5)
                    # Verify
                    autocomplete_input = self.wait_for_visible(locator, timeout=5)
                    selected_value = autocomplete_input.get_attribute("value")
                    if selected_value and value.lower() in selected_value.lower():
                        logger.info(f"{field_name} selected - field shows: {selected_value}")
                        return
                except Exception as retry_error:
                    raise PortalChangedError(f"Failed to select {field_name} after retry: {retry_error}") from retry_error
            raise PortalChangedError(f"Failed to select {field_name}: {e}") from e

    def _fill_service_line(self, service_line: ServiceLine, index: int) -> None:
        """
        Fill a single service line at the given index.

        Args:
            service_line: ServiceLine data to fill
            index: Service line index (0-based)
        """
        try:
            logger.info(f"Filling service line {index + 1}")

            # Build dynamic selectors based on index
            from_date_locator = (By.NAME, f"claimInformation.serviceLines.{index}.fromDate")
            place_of_service_code_locator = (By.NAME, f"claimInformation.serviceLines.{index}.placeOfServiceCode")
            procedure_code_locator = (By.NAME, f"claimInformation.serviceLines.{index}.procedureCode")
            diagnosis_code_pointer1_locator = (By.NAME, f"claimInformation.serviceLines.{index}.diagnosisCodePointer1")
            amount_locator = (By.NAME, f"claimInformation.serviceLines.{index}.amount")
            quantity_locator = (By.NAME, f"claimInformation.serviceLines.{index}.quantity")
            quantity_type_code_locator = (By.NAME, f"claimInformation.serviceLines.{index}.quantityTypeCode")

            # From Date
            if service_line.from_date:
                try:
                    from_date_input = self.wait_for_visible(from_date_locator, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", from_date_input)
                    time.sleep(0.3)
                    from_date_str = service_line.from_date.strftime("%m/%d/%Y")
                    self.type(from_date_locator, from_date_str, clear_first=True)
                    logger.info(f"Service Line {index + 1} From Date filled: {from_date_str}")
                except Exception as e:
                    logger.warning(f"Could not fill service line {index + 1} from date: {e}")

            # Place of Service Code
            if service_line.place_of_service_code:
                self.select_autocomplete(
                    place_of_service_code_locator,
                    service_line.place_of_service_code,
                    f"Service Line {index + 1} Place of Service Code",
                )

            # Procedure Code
            if service_line.procedure_code:
                self.select_autocomplete(
                    procedure_code_locator,
                    service_line.procedure_code,
                    f"Service Line {index + 1} Procedure Code",
                )

            # Diagnosis Code Pointer 1
            if service_line.diagnosis_code_pointer1:
                self.select_autocomplete(
                    diagnosis_code_pointer1_locator,
                    service_line.diagnosis_code_pointer1,
                    f"Service Line {index + 1} Diagnosis Code Pointer 1",
                )

            # Amount
            if service_line.amount:
                try:
                    amount_input = self.wait_for_visible(amount_locator, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", amount_input)
                    time.sleep(0.3)
                    self.type(amount_locator, service_line.amount, clear_first=True)
                    logger.info(f"Service Line {index + 1} Amount filled: {service_line.amount}")
                except Exception as e:
                    logger.warning(f"Could not fill service line {index + 1} amount: {e}")

            # Quantity
            if service_line.quantity:
                try:
                    quantity_input = self.wait_for_visible(quantity_locator, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", quantity_input)
                    time.sleep(0.3)
                    self.type(quantity_locator, service_line.quantity, clear_first=True)
                    logger.info(f"Service Line {index + 1} Quantity filled: {service_line.quantity}")
                except Exception as e:
                    logger.warning(f"Could not fill service line {index + 1} quantity: {e}")

            # Quantity Type Code
            if service_line.quantity_type_code:
                self.select_autocomplete(
                    quantity_type_code_locator,
                    service_line.quantity_type_code,
                    f"Service Line {index + 1} Quantity Type Code",
                )

        except Exception as e:
            logger.warning(f"Error filling service line {index + 1}: {e}")

    def fill_submission_form(self, query: ClaimsQuery) -> None:
        """
        Fill the claims submission form.

        Args:
            query: ClaimsQuery with form data

        Raises:
            ValidationError: If required fields are missing
            PortalChangedError: If form elements not found
        """
        try:
            logger.info(f"Filling claims submission form for request ID: {query.request_id}")

            # Validate required fields
            if not query.transaction_type:
                raise ValidationError("Transaction type is required")

            # Select Transaction Type (required)
            self.select_autocomplete(self.TRANSACTION_TYPE_INPUT, query.transaction_type, "Transaction Type")

            # Wait for form to update after transaction type selection
            logger.info("Waiting for form fields to update after transaction type selection...")
            time.sleep(3)  # Allow form to populate/enable fields

            # Select Responsibility Sequence first (default is "Primary")
            if query.responsibility_sequence:
                self.select_autocomplete(
                    self.RESPONSIBILITY_SEQUENCE_INPUT, query.responsibility_sequence, "Responsibility Sequence"
                )
                time.sleep(1)  # Wait for form to update

            # Select Payer (may be enabled after transaction type is selected)
            if query.payer:
                # Wait for payer field to become enabled
                logger.info("Waiting for payer field to become enabled...")
                payer_input = None
                max_wait_attempts = 10
                for attempt in range(max_wait_attempts):
                    try:
                        # Try to find the payer input
                        try:
                            payer_input = self.wait_for_presence(self.PAYER_INPUT, timeout=2)
                        except:
                            payer_input = self.wait_for_presence(self.PAYER_INPUT_ALT, timeout=2)
                        
                        # Check if it's enabled
                        if payer_input and payer_input.is_enabled():
                            logger.info(f"Payer field is now enabled (attempt {attempt + 1})")
                            break
                        else:
                            logger.debug(f"Payer field still disabled, waiting... (attempt {attempt + 1}/{max_wait_attempts})")
                            time.sleep(1)
                    except:
                        time.sleep(1)
                
                # Now try to select the payer
                if payer_input and payer_input.is_enabled():
                    self.select_autocomplete(self.PAYER_INPUT, query.payer, "Payer")
                    time.sleep(1)  # Wait for form to update
                else:
                    logger.warning("Payer field is still disabled after waiting - skipping payer selection")

            # Patient Information
            if query.patient_last_name:
                try:
                    # Wait for field to be visible and enabled
                    patient_last_name_input = self.wait_for_visible(self.PATIENT_LAST_NAME_INPUT, timeout=10)
                    # Scroll into view if needed
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", patient_last_name_input)
                    time.sleep(0.5)
                    
                    # Clear any existing value first
                    self.driver.execute_script("arguments[0].value = '';", patient_last_name_input)
                    self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", patient_last_name_input)
                    time.sleep(0.2)
                    
                    # Focus and type
                    self.driver.execute_script("arguments[0].focus();", patient_last_name_input)
                    time.sleep(0.2)
                    patient_last_name_input.clear()
                    time.sleep(0.2)
                    patient_last_name_input.send_keys(query.patient_last_name)
                    time.sleep(0.3)
                    
                    # Verify it was filled
                    filled_value = patient_last_name_input.get_attribute("value")
                    if filled_value == query.patient_last_name:
                        logger.info(f"Patient Last Name filled successfully: {query.patient_last_name}")
                    else:
                        logger.warning(f"Patient Last Name may not have filled correctly. Expected: {query.patient_last_name}, Got: {filled_value}")
                        # Try one more time with direct JavaScript
                        self.driver.execute_script(f"arguments[0].value = '{query.patient_last_name}';", patient_last_name_input)
                        self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", patient_last_name_input)
                        self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", patient_last_name_input)
                        logger.info(f"Patient Last Name filled via JavaScript: {query.patient_last_name}")
                except Exception as e:
                    logger.error(f"Could not fill patient last name: {e}")
                    raise

            if query.patient_first_name:
                try:
                    patient_first_name_input = self.wait_for_visible(self.PATIENT_FIRST_NAME_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", patient_first_name_input)
                    time.sleep(0.3)
                    self.type(self.PATIENT_FIRST_NAME_INPUT, query.patient_first_name, clear_first=True)
                    logger.info(f"Patient First Name filled: {query.patient_first_name}")
                except Exception as e:
                    logger.warning(f"Could not fill patient first name: {e}")

            if query.patient_birth_date:
                try:
                    patient_birth_date_input = self.wait_for_visible(self.PATIENT_BIRTH_DATE_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", patient_birth_date_input)
                    time.sleep(0.3)
                    # Format date as mm/dd/yyyy
                    birth_date_str = query.patient_birth_date.strftime("%m/%d/%Y")
                    self.type(self.PATIENT_BIRTH_DATE_INPUT, birth_date_str, clear_first=True)
                    logger.info(f"Patient Birth Date filled: {birth_date_str}")
                except Exception as e:
                    logger.warning(f"Could not fill patient birth date: {e}")

            if query.patient_gender_code:
                self.select_autocomplete(self.PATIENT_GENDER_CODE_INPUT, query.patient_gender_code, "Patient Gender Code")

            if query.patient_subscriber_relationship_code:
                self.select_autocomplete(
                    self.PATIENT_SUBSCRIBER_RELATIONSHIP_CODE_INPUT,
                    query.patient_subscriber_relationship_code,
                    "Patient Subscriber Relationship Code",
                )

            # Subscriber Information
            if query.subscriber_member_id:
                try:
                    subscriber_member_id_input = self.wait_for_visible(self.SUBSCRIBER_MEMBER_ID_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", subscriber_member_id_input)
                    time.sleep(0.3)
                    self.type(self.SUBSCRIBER_MEMBER_ID_INPUT, query.subscriber_member_id, clear_first=True)
                    logger.info(f"Subscriber Member ID filled: {query.subscriber_member_id}")
                except Exception as e:
                    logger.warning(f"Could not fill subscriber member ID: {e}")

            if query.subscriber_group_number:
                try:
                    subscriber_group_number_input = self.wait_for_visible(self.SUBSCRIBER_GROUP_NUMBER_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", subscriber_group_number_input)
                    time.sleep(0.3)
                    self.type(self.SUBSCRIBER_GROUP_NUMBER_INPUT, query.subscriber_group_number, clear_first=True)
                    logger.info(f"Subscriber Group Number filled: {query.subscriber_group_number}")
                except Exception as e:
                    logger.warning(f"Could not fill subscriber group number: {e}")

            # Patient Address
            if query.patient_address_line1:
                try:
                    patient_address_input = self.wait_for_visible(self.PATIENT_ADDRESS_LINE1_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", patient_address_input)
                    time.sleep(0.3)
                    self.type(self.PATIENT_ADDRESS_LINE1_INPUT, query.patient_address_line1, clear_first=True)
                    logger.info(f"Patient Address Line 1 filled: {query.patient_address_line1}")
                except Exception as e:
                    logger.warning(f"Could not fill patient address line 1: {e}")

            if query.patient_country_code:
                self.select_autocomplete(self.PATIENT_COUNTRY_CODE_INPUT, query.patient_country_code, "Patient Country Code")

            if query.patient_city:
                try:
                    patient_city_input = self.wait_for_visible(self.PATIENT_CITY_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", patient_city_input)
                    time.sleep(0.3)
                    self.type(self.PATIENT_CITY_INPUT, query.patient_city, clear_first=True)
                    logger.info(f"Patient City filled: {query.patient_city}")
                except Exception as e:
                    logger.warning(f"Could not fill patient city: {e}")

            if query.patient_state_code:
                self.select_autocomplete(self.PATIENT_STATE_CODE_INPUT, query.patient_state_code, "Patient State Code")

            if query.patient_zip_code:
                try:
                    patient_zip_input = self.wait_for_visible(self.PATIENT_ZIP_CODE_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", patient_zip_input)
                    time.sleep(0.3)
                    self.type(self.PATIENT_ZIP_CODE_INPUT, query.patient_zip_code, clear_first=True)
                    logger.info(f"Patient Zip Code filled: {query.patient_zip_code}")
                except Exception as e:
                    logger.warning(f"Could not fill patient zip code: {e}")

            # Claim Information
            if query.patient_paid_amount:
                try:
                    patient_paid_amount_input = self.wait_for_visible(self.PATIENT_PAID_AMOUNT_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", patient_paid_amount_input)
                    time.sleep(0.3)
                    self.type(self.PATIENT_PAID_AMOUNT_INPUT, query.patient_paid_amount, clear_first=True)
                    logger.info(f"Patient Paid Amount filled: {query.patient_paid_amount}")
                except Exception as e:
                    logger.warning(f"Could not fill patient paid amount: {e}")

            if query.benefits_assignment_certification:
                self.select_autocomplete(
                    self.BENEFITS_ASSIGNMENT_CERTIFICATION_INPUT,
                    query.benefits_assignment_certification,
                    "Benefits Assignment Certification",
                )

            if query.claim_control_number:
                try:
                    claim_control_number_input = self.wait_for_visible(self.CLAIM_CONTROL_NUMBER_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", claim_control_number_input)
                    time.sleep(0.3)
                    self.type(self.CLAIM_CONTROL_NUMBER_INPUT, query.claim_control_number, clear_first=True)
                    logger.info(f"Claim Control Number filled: {query.claim_control_number}")
                except Exception as e:
                    logger.warning(f"Could not fill claim control number: {e}")

            if query.place_of_service_code:
                self.select_autocomplete(
                    self.PLACE_OF_SERVICE_CODE_INPUT,
                    query.place_of_service_code,
                    "Place of Service Code",
                )

            if query.frequency_type_code:
                self.select_autocomplete(
                    self.FREQUENCY_TYPE_CODE_INPUT,
                    query.frequency_type_code,
                    "Frequency Type Code",
                )

            if query.provider_accept_assignment_code:
                self.select_autocomplete(
                    self.PROVIDER_ACCEPT_ASSIGNMENT_CODE_INPUT,
                    query.provider_accept_assignment_code,
                    "Provider Accept Assignment Code",
                )

            if query.information_release_code:
                self.select_autocomplete(
                    self.INFORMATION_RELEASE_CODE_INPUT,
                    query.information_release_code,
                    "Information Release Code",
                )

            if query.provider_signature_on_file:
                self.select_autocomplete(
                    self.PROVIDER_SIGNATURE_ON_FILE_INPUT,
                    query.provider_signature_on_file,
                    "Provider Signature On File",
                )

            if query.payer_claim_filing_indicator_code:
                self.select_autocomplete(
                    self.PAYER_CLAIM_FILING_INDICATOR_CODE_INPUT,
                    query.payer_claim_filing_indicator_code,
                    "Payer Claim Filing Indicator Code",
                )

            if query.medical_record_number:
                try:
                    medical_record_number_input = self.wait_for_visible(self.MEDICAL_RECORD_NUMBER_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", medical_record_number_input)
                    time.sleep(0.3)
                    self.type(self.MEDICAL_RECORD_NUMBER_INPUT, query.medical_record_number, clear_first=True)
                    logger.info(f"Medical Record Number filled: {query.medical_record_number}")
                except Exception as e:
                    logger.warning(f"Could not fill medical record number: {e}")

            # Billing Provider Information
            if query.billing_provider_last_name:
                try:
                    billing_provider_last_name_input = self.wait_for_visible(self.BILLING_PROVIDER_LAST_NAME_INPUT, timeout=10)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", billing_provider_last_name_input)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].value = '';", billing_provider_last_name_input)
                    self.driver.execute_script("arguments[0].focus();", billing_provider_last_name_input)
                    time.sleep(0.2)
                    billing_provider_last_name_input.clear()
                    time.sleep(0.2)
                    billing_provider_last_name_input.send_keys(query.billing_provider_last_name)
                    logger.info(f"Billing Provider Last Name filled: {query.billing_provider_last_name}")
                except Exception as e:
                    logger.warning(f"Could not fill billing provider last name: {e}")

            if query.billing_provider_first_name:
                try:
                    billing_provider_first_name_input = self.wait_for_visible(self.BILLING_PROVIDER_FIRST_NAME_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", billing_provider_first_name_input)
                    time.sleep(0.3)
                    self.type(self.BILLING_PROVIDER_FIRST_NAME_INPUT, query.billing_provider_first_name, clear_first=True)
                    logger.info(f"Billing Provider First Name filled: {query.billing_provider_first_name}")
                except Exception as e:
                    logger.warning(f"Could not fill billing provider first name: {e}")

            if query.billing_provider_npi:
                try:
                    billing_provider_npi_input = self.wait_for_visible(self.BILLING_PROVIDER_NPI_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", billing_provider_npi_input)
                    time.sleep(0.3)
                    self.type(self.BILLING_PROVIDER_NPI_INPUT, query.billing_provider_npi, clear_first=True)
                    logger.info(f"Billing Provider NPI filled: {query.billing_provider_npi}")
                except Exception as e:
                    logger.warning(f"Could not fill billing provider NPI: {e}")

            if query.billing_provider_tax_id_ein:
                try:
                    billing_provider_ein_input = self.wait_for_visible(self.BILLING_PROVIDER_TAX_ID_EIN_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", billing_provider_ein_input)
                    time.sleep(0.3)
                    self.type(self.BILLING_PROVIDER_TAX_ID_EIN_INPUT, query.billing_provider_tax_id_ein, clear_first=True)
                    logger.info(f"Billing Provider Tax ID EIN filled: {query.billing_provider_tax_id_ein}")
                except Exception as e:
                    logger.warning(f"Could not fill billing provider Tax ID EIN: {e}")

            if query.billing_provider_tax_id_ssn:
                try:
                    billing_provider_ssn_input = self.wait_for_visible(self.BILLING_PROVIDER_TAX_ID_SSN_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", billing_provider_ssn_input)
                    time.sleep(0.3)
                    self.type(self.BILLING_PROVIDER_TAX_ID_SSN_INPUT, query.billing_provider_tax_id_ssn, clear_first=True)
                    logger.info(f"Billing Provider Tax ID SSN filled: {query.billing_provider_tax_id_ssn}")
                except Exception as e:
                    logger.warning(f"Could not fill billing provider Tax ID SSN: {e}")

            if query.billing_provider_specialty_code:
                self.select_autocomplete(
                    self.BILLING_PROVIDER_SPECIALTY_CODE_INPUT,
                    query.billing_provider_specialty_code,
                    "Billing Provider Specialty Code",
                )

            if query.billing_provider_address_line1:
                try:
                    billing_provider_address_input = self.wait_for_visible(self.BILLING_PROVIDER_ADDRESS_LINE1_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", billing_provider_address_input)
                    time.sleep(0.3)
                    self.type(self.BILLING_PROVIDER_ADDRESS_LINE1_INPUT, query.billing_provider_address_line1, clear_first=True)
                    logger.info(f"Billing Provider Address Line 1 filled: {query.billing_provider_address_line1}")
                except Exception as e:
                    logger.warning(f"Could not fill billing provider address line 1: {e}")

            if query.billing_provider_country_code:
                self.select_autocomplete(
                    self.BILLING_PROVIDER_COUNTRY_CODE_INPUT,
                    query.billing_provider_country_code,
                    "Billing Provider Country Code",
                )

            if query.billing_provider_city:
                try:
                    billing_provider_city_input = self.wait_for_visible(self.BILLING_PROVIDER_CITY_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", billing_provider_city_input)
                    time.sleep(0.3)
                    self.type(self.BILLING_PROVIDER_CITY_INPUT, query.billing_provider_city, clear_first=True)
                    logger.info(f"Billing Provider City filled: {query.billing_provider_city}")
                except Exception as e:
                    logger.warning(f"Could not fill billing provider city: {e}")

            if query.billing_provider_state_code:
                self.select_autocomplete(
                    self.BILLING_PROVIDER_STATE_CODE_INPUT,
                    query.billing_provider_state_code,
                    "Billing Provider State Code",
                )

            if query.billing_provider_zip_code:
                try:
                    billing_provider_zip_input = self.wait_for_visible(self.BILLING_PROVIDER_ZIP_CODE_INPUT, timeout=5)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", billing_provider_zip_input)
                    time.sleep(0.3)
                    self.type(self.BILLING_PROVIDER_ZIP_CODE_INPUT, query.billing_provider_zip_code, clear_first=True)
                    logger.info(f"Billing Provider Zip Code filled: {query.billing_provider_zip_code}")
                except Exception as e:
                    logger.warning(f"Could not fill billing provider zip code: {e}")

            # Diagnosis Information
            if query.diagnosis_code:
                self.select_autocomplete(self.DIAGNOSIS_CODE_INPUT, query.diagnosis_code, "Diagnosis Code")

            # Service Lines
            if query.service_lines:
                for index, service_line in enumerate(query.service_lines):
                    if index > 0:
                        # Click "Add a Line" button to add another service line
                        try:
                            add_line_button = self.wait_for_clickable(self.ADD_SERVICE_LINE_BUTTON, timeout=5)
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_line_button)
                            time.sleep(0.3)
                            add_line_button.click()
                            logger.info(f"Clicked 'Add a Line' button to add service line {index + 1}")
                            time.sleep(1)  # Wait for new line to appear
                        except Exception as e:
                            logger.warning(f"Could not click 'Add a Line' button: {e}")
                            continue

                    # Fill service line fields (using dynamic index)
                    self._fill_service_line(service_line, index)

            logger.info("Form filled successfully")

        except ValidationError:
            raise
        except Exception as e:
            raise PortalChangedError(f"Failed to fill claims form: {e}") from e

    def submit_and_wait(self, timeout: int = 60, skip_if_not_found: bool = True) -> None:
        """
        Submit the claims form and wait for results.

        Args:
            timeout: Maximum time to wait for results in seconds
            skip_if_not_found: If True, skip submission if submit button is not found (for incomplete forms)

        Raises:
            PortalChangedError: If submission fails
            PortalBusinessError: If portal returns business error
        """
        try:
            logger.info("Looking for submit button...")

            # Find and click submit button
            submit_button = None
            try:
                # Try CSS selector first
                submit_button = self.wait_for_clickable(self.SUBMIT_BUTTON, timeout=3)
                logger.info("Found submit button by CSS selector")
            except:
                try:
                    # Try XPath by text content
                    submit_button = self.wait_for_clickable(self.SUBMIT_BUTTON_XPATH, timeout=3)
                    logger.info("Found submit button by XPath")
                except:
                    # Try to find any button with type submit
                    try:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                        logger.info("Found submit button by type attribute")
                    except:
                        if skip_if_not_found:
                            logger.info("Submit button not found - skipping submission (form may be incomplete)")
                            return
                        else:
                            raise PortalChangedError("Could not find submit button with any selector")

            if submit_button:
                submit_button.click()
                logger.info("Submit button clicked")

                # Wait for results to load
                logger.info("Waiting for submission results to load...")
                time.sleep(3)  # Initial wait for page to start loading

                # Wait for either success message, error message, or results container
                try:
                    WebDriverWait(self.driver, timeout).until(
                        lambda d: (
                            self.exists(self.SUCCESS_MESSAGE, timeout=1)
                            or self.exists(self.ERROR_MESSAGE, timeout=1)
                            or self.exists(self.RESULTS_CONTAINER, timeout=1)
                        )
                    )
                except:
                    logger.warning("Timeout waiting for results, but continuing...")

                # Additional wait for results to fully render
                logger.info("Waiting additional time for results to fully render...")
                time.sleep(3)
            else:
                if skip_if_not_found:
                    logger.info("Submit button element is None - skipping submission")
                    return
                else:
                    raise PortalChangedError("Submit button element is None")

        except PortalChangedError:
            raise
        except Exception as e:
            if skip_if_not_found:
                logger.warning(f"Error during submission attempt: {e}, but continuing...")
            else:
                raise PortalChangedError(f"Failed to submit claims form: {e}") from e

    def parse_result(self, query: ClaimsQuery) -> ClaimsResult:
        """
        Parse the claims submission result from the page.

        Args:
            query: Original query

        Returns:
            ClaimsResult with parsed data

        Raises:
            PortalBusinessError: If portal returned an error
        """
        try:
            logger.info(f"Parsing claims submission result for request ID: {query.request_id}")

            # Check for error messages first
            if self.exists(self.ERROR_MESSAGE, timeout=2):
                error_element = self.driver.find_element(*self.ERROR_MESSAGE)
                error_text = error_element.text.strip()
                logger.warning(f"Portal returned error: {error_text}")
                raise PortalBusinessError(f"Portal error: {error_text}")

            # Try to extract claim ID or confirmation number
            claim_id = None
            try:
                if self.exists(self.CLAIM_ID_TEXT, timeout=2):
                    claim_id_element = self.driver.find_element(*self.CLAIM_ID_TEXT)
                    # Try to extract ID from text or nearby elements
                    claim_id_text = claim_id_element.text
                    # Look for patterns like "Claim ID: 123456" or "Confirmation: ABC123"
                    import re
                    match = re.search(r"(?:Claim ID|Confirmation|ID)[\s:]+([A-Z0-9-]+)", claim_id_text, re.IGNORECASE)
                    if match:
                        claim_id = match.group(1)
            except:
                pass

            # Determine submission status
            submission_status = None
            if self.exists(self.SUCCESS_MESSAGE, timeout=2):
                submission_status = "SUBMITTED"
            elif claim_id:
                submission_status = "SUBMITTED"
            else:
                # If no submit button was found, form is likely incomplete
                submission_status = "FORM_INCOMPLETE"  # Indicates form filled but not submitted

            result = ClaimsResult(
                request_id=query.request_id,
                submission_status=submission_status,
                claim_id=claim_id,
                error_message=None,
            )

            logger.info(f"Parsed result for request {query.request_id}: status={submission_status}, claim_id={claim_id}")
            return result

        except PortalBusinessError:
            raise
        except Exception as e:
            logger.warning(f"Error parsing result: {e}, returning default result")
            # Return a result with unknown status
            return ClaimsResult(
                request_id=query.request_id,
                submission_status="FORM_INCOMPLETE",
                claim_id=None,
                error_message=None,
            )

