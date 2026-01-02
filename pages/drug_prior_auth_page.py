"""Drug Prior Authorization page object for form filling and result parsing."""

import time
from typing import Optional

from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.errors import PortalBusinessError, PortalChangedError, ValidationError
from domain.drug_prior_auth_models import DrugPriorAuthQuery, DrugPriorAuthResult

from .base_page import BasePage


class DrugPriorAuthPage(BasePage):
    """Page object for Availity drug prior authorization form and results."""

    # Agreement/Redirection page selectors (after selecting provider)
    AGREEMENT_PAGE_TEXT = (
        By.XPATH,
        "//*[contains(text(), 'You are about to be re-directed to a third-party site')]"
    )
    PROCEED_TO_NOVOLOGIX_BUTTON = (
        By.XPATH,
        "//button[contains(text(), 'Proceed to Novologix')]"
    )
    PROCEED_BUTTON_ALT = (
        By.CSS_SELECTOR,
        "button[class*='proceed'], button[class*='novologix'], button.btn-primary"
    )

    # Provider search results selectors 
    PROVIDER_SEARCH_RESULTS_TABLE = (
        By.CSS_SELECTOR,
        "table, [class*='table'], [class*='results'], [class*='provider-list']"
    )
    PROVIDER_RESULT_ROWS = (
        By.CSS_SELECTOR,
        "tbody tr, [class*='row'], [class*='provider-row']"
    )
    PROVIDER_RESULT_NAME = (
        By.CSS_SELECTOR,
        "td:first-child, [class*='provider-name'], [class*='name']"
    )
    PROVIDER_RESULT_NPI = (
        By.CSS_SELECTOR,
        "[class*='npi'], [contains(text(), 'NPI')]"
    )
    PROVIDER_RESULT_ADDRESS = (
        By.CSS_SELECTOR,
        "td:nth-child(2), [class*='address']"
    )
    PROVIDER_SELECT_BUTTON = (
        By.XPATH,
        "//button[contains(text(), 'Select')]"
    )
    PROVIDER_RESULTS_CONTAINER = (
        By.CSS_SELECTOR,
        "[class*='provider-results'], [class*='search-results'], [id*='results']"
    )

    # Provider form selectors (after clicking Novologix)
    PROVIDER_SELECT_DROPDOWN = (
        By.CSS_SELECTOR,
        "input[placeholder*='Select Provider'], input[id*='provider'], select[id*='provider']"
    )
    PROVIDER_NPI_INPUT = (
        By.CSS_SELECTOR,
        "input[id*='npi'], input[name*='npi'], input[placeholder*='NPI']"
    )
    RETRIEVE_PROVIDER_INFO_BUTTON = (
        By.XPATH,
        "//button[contains(text(), 'Retrieve Provider Info')]"
    )
    SHOW_OPTIONAL_FIELDS_CHECKBOX = (
        By.CSS_SELECTOR,
        "input[type='checkbox'][id*='optional'], input[type='checkbox'][name*='optional']"
    )

    # Select2 dropdown selectors (different from React Select)
    ORGANIZATION_SELECT2_CONTAINER = (
        By.CSS_SELECTOR,
        "span.select2-chosen#select2-chosen-1, span[id^='select2-chosen']",
    )
    ORGANIZATION_SELECT2_SEARCH_INPUT = (
        By.CSS_SELECTOR,
        "input#s2id_autogen1_search, input.select2-input",
    )

    PAYER_SELECT2_CONTAINER = (
        By.CSS_SELECTOR,
        "span.select2-chosen#select2-chosen-2, span.select2-chosen:not(#select2-chosen-1)",
    )
    PAYER_SELECT2_SEARCH_INPUT = (
        By.CSS_SELECTOR,
        "input#s2id_autogen2_search, input.select2-input",
    )

    # Select2 results
    SELECT2_RESULTS = (By.CSS_SELECTOR, "ul.select2-results li.select2-result")
    SELECT2_RESULT_LABEL = (By.CSS_SELECTOR, ".select2-result-label")

    # Next button
    NEXT_BUTTON = (
        By.CSS_SELECTOR,
        "button:contains('Next'), button.btn-primary, button[type='submit']",
    )
    NEXT_BUTTON_XPATH = (By.XPATH, "//button[contains(text(), 'Next')]")

    # Error messages
    ERROR_MESSAGE = (
        By.CSS_SELECTOR,
        ".error-message, .alert-danger, [role='alert'], [class*='error']",
    )

    def __init__(self, driver: WebDriver):
        """
        Initialize drug prior auth page.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def ensure_loaded(self) -> None:
        """
        Ensure the drug prior auth form is loaded.

        Raises:
            PortalChangedError: If form elements not found
        """
        try:
            logger.info("Waiting for drug prior auth form to load...")
            logger.info(f"Current URL: {self.driver.current_url}")

            # Check if form is in an iframe
            from selenium.webdriver.common.by import By as ByLocator

            try:
                self.driver.switch_to.default_content()
            except:
                pass

            iframes = self.driver.find_elements(ByLocator.TAG_NAME, "iframe")
            if iframes:
                logger.info(f"Found {len(iframes)} iframe(s), switching to first iframe...")
                self.driver.switch_to.frame(iframes[0])
                logger.info("Switched to iframe")
                time.sleep(2)

            # Wait for Select2 containers to appear
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    logger.debug(
                        f"Attempt {attempt + 1}/{max_attempts} to find Select2 containers..."
                    )
                    # Try to find payer Select2 container (most important)
                    self.wait_for_presence(self.PAYER_SELECT2_CONTAINER, timeout=5)
                    logger.info("Found Select2 containers - form is loaded!")
                    break
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise PortalChangedError(
                            f"Drug prior auth form not found after {max_attempts} attempts. Current URL: {self.driver.current_url}"
                        )
                    time.sleep(1)

            logger.info("Drug prior auth form loaded successfully!")

        except Exception as e:
            logger.error(
                f"Drug prior auth form not loaded. Current URL: {self.driver.current_url}"
            )
            raise PortalChangedError(f"Drug prior auth form not loaded: {e}") from e

    def select_select2_option(
        self, container_locator: tuple, search_input_locator: tuple, option_text: str
    ) -> None:
        """
        Select an option from a Select2 dropdown.

        Args:
            container_locator: Locator for the Select2 container (the clickable span)
            search_input_locator: Locator for the Select2 search input
            option_text: Text of the option to select

        Raises:
            PortalChangedError: If selection fails
        """
        try:
            logger.info(f"Selecting Select2 option: {option_text}")

            # Click the Select2 container to open dropdown
            container = self.wait_for_clickable(container_locator, timeout=5)
            container.click()
            time.sleep(0.5)  # Wait for dropdown to open

            # Find and interact with the search input
            search_input = self.wait_for_visible(search_input_locator, timeout=3)

            # Clear and type the search text
            search_input.clear()
            search_input.send_keys(option_text)
            time.sleep(0.5)  # Wait for results to filter

            # Wait for results to appear
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(self.SELECT2_RESULTS)
            )

            # Find the matching option
            results = self.driver.find_elements(*self.SELECT2_RESULTS)
            option_found = False

            for result in results:
                try:
                    label = result.find_element(*self.SELECT2_RESULT_LABEL)
                    label_text = label.text.strip()

                    # Check for exact or partial match
                    if option_text.upper() in label_text.upper() or label_text.upper() in option_text.upper():
                        logger.info(f"Found matching option: {label_text}")
                        result.click()
                        option_found = True
                        time.sleep(0.5)  # Wait for selection to register
                        break
                except Exception as e:
                    logger.debug(f"Error checking result option: {e}")
                    continue

            if not option_found:
                # Try pressing Enter on the search input (might select first result)
                logger.warning(
                    f"Exact match not found for '{option_text}', trying Enter key..."
                )
                search_input.send_keys(Keys.ENTER)
                time.sleep(0.5)

            logger.info(f"Successfully selected: {option_text}")

        except Exception as e:
            logger.error(f"Failed to select Select2 option '{option_text}': {e}")
            raise PortalChangedError(
                f"Failed to select Select2 option '{option_text}': {e}"
            ) from e

    def select_organization(self, organization_name: Optional[str] = None) -> None:
        """
        Select organization from Select2 dropdown.

        Args:
            organization_name: Organization name to select (if None, uses default/pre-filled value)

        Raises:
            PortalChangedError: If organization selection fails
        """
        if organization_name:
            logger.info(f"Selecting organization: {organization_name}")
            self.select_select2_option(
                self.ORGANIZATION_SELECT2_CONTAINER,
                self.ORGANIZATION_SELECT2_SEARCH_INPUT,
                organization_name,
            )
        else:
            logger.info("Organization already selected or not required to change")

    def select_payer(self, payer_name: str) -> None:
        """
        Select payer from Select2 dropdown.

        Args:
            payer_name: Payer name to select

        Raises:
            PortalChangedError: If payer selection fails
        """
        logger.info(f"Selecting payer: {payer_name}")
        self.select_select2_option(
            self.PAYER_SELECT2_CONTAINER,
            self.PAYER_SELECT2_SEARCH_INPUT,
            payer_name,
        )

    def click_next(self) -> None:
        """
        Click the Next button to proceed to next step.

        Raises:
            PortalChangedError: If Next button not found or click fails
        """
        try:
            logger.info("Clicking Next button...")

            # Try XPath first (more reliable for text matching)
            try:
                next_button = self.wait_for_clickable(self.NEXT_BUTTON_XPATH, timeout=5)
                next_button.click()
            except:
                # Fallback to CSS selector
                next_button = self.wait_for_clickable(
                    (By.CSS_SELECTOR, "button.btn-primary, button[type='submit']"),
                    timeout=5,
                )
                next_button.click()

            logger.info("Next button clicked successfully")
            time.sleep(2)  # Wait for next page to load

        except Exception as e:
            logger.error(f"Failed to click Next button: {e}")
            raise PortalChangedError(f"Failed to click Next button: {e}") from e

    def fill_payer_selection_form(self, query: DrugPriorAuthQuery) -> None:
        """
        Fill the payer selection form (first step).

        Args:
            query: DrugPriorAuthQuery with payer information

        Raises:
            ValidationError: If required fields missing
            PortalChangedError: If form filling fails
        """
        try:
            logger.info("Filling payer selection form...")

            # Select organization if provided
            if query.organization_name:
                self.select_organization(query.organization_name)

            # Select payer (required)
            if not query.payer_name:
                raise ValidationError("Payer name is required")
            self.select_payer(query.payer_name)

            logger.info("Payer selection form filled successfully")

        except (ValidationError, PortalChangedError):
            raise
        except Exception as e:
            logger.error(f"Failed to fill payer selection form: {e}")
            raise PortalChangedError(f"Failed to fill payer selection form: {e}") from e

    def wait_for_next_step(self, timeout: int = 30) -> None:
        """
        Wait for the next step/form to load after clicking Next.

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            PortalChangedError: If next step doesn't load
        """
        try:
            logger.info("Waiting for next step to load...")
            # Wait for URL to change or new form elements to appear
            initial_url = self.driver.current_url
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.current_url != initial_url
                or len(d.find_elements(By.CSS_SELECTOR, "input, select, textarea")) > 0
            )
            time.sleep(2)  # Additional wait for form to fully render
            logger.info("Next step loaded successfully")

        except Exception as e:
            logger.error(f"Next step did not load: {e}")
            raise PortalChangedError(f"Next step did not load: {e}") from e

    def parse_result(self, query: DrugPriorAuthQuery) -> DrugPriorAuthResult:
        """
        Parse the drug prior authorization result.

        TODO: Update this method after seeing the actual results page structure.

        Args:
            query: Original query

        Returns:
            DrugPriorAuthResult with parsed data
        """
        try:
            logger.info("Parsing drug prior auth result...")

            # TODO: Implement actual result parsing
            # This is a placeholder - update after seeing results page
            result = DrugPriorAuthResult(
                request_id=query.request_id,
                prior_auth_status=None,
                prior_auth_number=None,
                approval_date=None,
                expiration_date=None,
            )

            logger.info("Result parsed successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to parse result: {e}")
            raise PortalChangedError(f"Failed to parse result: {e}") from e

    # Routing page selectors (after clicking Next)
    ROUTING_PAGE_TITLE = (By.XPATH, "//*[contains(text(), 'Medically Covered Injectable Specialty Drug')]")
    NOVOLOGIX_BUTTON = (By.XPATH, "//button[contains(text(), 'Novologix')]")
    BACK_BUTTON = (By.XPATH, "//button[contains(text(), 'Back')]")
    AUTHORIZATION_REQUEST_LINK = (By.XPATH, "//*[contains(text(), 'Authorization Request')]")

    def is_on_routing_page(self) -> bool:
        """
        Check if currently on the routing/informational page (after selecting payer).

        Returns:
            True if on routing page, False otherwise
        """
        try:
            # Check for the routing page title
            return self.exists(self.ROUTING_PAGE_TITLE, timeout=3)
        except:
            return False

    def determine_routing_path(
        self, 
        drug_type: Optional[str] = None,
        member_state: Optional[str] = None,
        member_type: Optional[str] = None  # "Commercial", "Medicare", "Exchange"
    ) -> str:
        """
        Determine which path to take based on drug type and member information.

        Args:
            drug_type: Type of drug (e.g., "injectable", "radiation_oncology", "other")
            member_state: Member's state (e.g., "AZ", "CT", "IL", "PA", "TX")
            member_type: Member type (e.g., "Commercial", "Medicare", "Exchange")

        Returns:
            "novologix" or "authorization_request"
        """
        # Check if drug is medically covered injectable or radiation oncology
        if drug_type in ["injectable", "radiation_oncology"]:
            # Check state eligibility for Novologix
            if drug_type == "injectable":
                # Injectable: Fully-insured Commercial in AZ, or Medicare in AZ/CT/IL/PA/TX
                if member_type == "Commercial" and member_state == "AZ":
                    return "novologix"
                elif member_type == "Medicare" and member_state in ["AZ", "CT", "IL", "PA", "TX"]:
                    return "novologix"
                elif member_type == "Exchange" and member_state in ["AZ", "CT", "IL", "PA", "TX"]:
                    return "novologix"
            
            if drug_type == "radiation_oncology":
                # Radiation Oncology: Same eligibility as injectable
                if member_type == "Commercial" and member_state == "AZ":
                    return "novologix"
                elif member_type == "Medicare" and member_state in ["AZ", "CT", "IL", "PA", "TX"]:
                    return "novologix"
                elif member_type == "Exchange" and member_state in ["AZ", "CT", "IL", "PA", "TX"]:
                    return "novologix"
        
        # Default to Authorization Request for other cases
        return "authorization_request"

    def click_novologix_button(self) -> None:
        """
        Click the Novologix button to navigate to the form.

        Raises:
            PortalChangedError: If button not found or click fails
        """
        try:
            logger.info("Clicking Novologix button...")
            novologix_button = self.wait_for_clickable(self.NOVOLOGIX_BUTTON, timeout=5)
            novologix_button.click()
            logger.info("Novologix button clicked - navigating to provider form")
            time.sleep(3)  # Wait for navigation
            
        except Exception as e:
            logger.error(f"Failed to click Novologix button: {e}")
            raise PortalChangedError(f"Failed to click Novologix button: {e}") from e

    def click_back_button(self) -> None:
        """
        Click the Back button to return to previous page.

        Raises:
            PortalChangedError: If button not found or click fails
        """
        try:
            logger.info("Clicking Back button...")
            back_button = self.wait_for_clickable(self.BACK_BUTTON, timeout=5)
            back_button.click()
            logger.info("Back button clicked")
            time.sleep(2)  # Wait for navigation
            
        except Exception as e:
            logger.error(f"Failed to click Back button: {e}")
            raise PortalChangedError(f"Failed to click Back button: {e}") from e

    def navigate_to_authorization_request(self) -> None:
        """
        Navigate to the Authorization Request section (for non-Novologix requests).

        This involves going back and finding the Authorization Request option.

        Raises:
            PortalChangedError: If navigation fails
        """
        try:
            logger.info("Navigating to Authorization Request...")
            
            # First, click Back to return to Authorizations & Referrals screen
            self.click_back_button()
            
            # TODO: After seeing the Authorizations & Referrals screen,
            # add logic to find and click "Authorization Request" link/button
            # For now, this is a placeholder
            
            logger.warning("Navigation to Authorization Request not yet implemented - need to see the screen structure")
            
        except Exception as e:
            logger.error(f"Failed to navigate to Authorization Request: {e}")
            raise PortalChangedError(f"Failed to navigate to Authorization Request: {e}") from e

    def handle_routing_page(
        self,
        drug_type: Optional[str] = None,
        member_state: Optional[str] = None,
        member_type: Optional[str] = None
    ) -> str:
        """
        Handle the routing page after selecting payer.

        Determines which path to take and navigates accordingly.

        Args:
            drug_type: Type of drug/service
            member_state: Member's state
            member_type: Member type (Commercial, Medicare, Exchange)

        Returns:
            "novologix" or "authorization_request" - the path taken
        """
        try:
            logger.info("Handling routing page...")
            
            if not self.is_on_routing_page():
                logger.warning("Not on routing page - may have navigated directly to form")
                return "unknown"
            
            # Determine which path to take
            path = self.determine_routing_path(drug_type, member_state, member_type)
            logger.info(f"Determined routing path: {path}")
            
            if path == "novologix":
                self.click_novologix_button()
                return "novologix"
            else:
                # Navigate to Authorization Request
                self.navigate_to_authorization_request()
                return "authorization_request"
                
        except Exception as e:
            logger.error(f"Failed to handle routing page: {e}")
            raise PortalChangedError(f"Failed to handle routing page: {e}") from e
    
    def is_on_provider_form(self) -> bool:
        """
        Check if currently on the provider form page (after Novologix).

        Returns:
            True if on provider form, False otherwise
        """
        try:
            # Check for Provider NPI field
            return self.exists(self.PROVIDER_NPI_INPUT, timeout=3)
        except:
            return False

    def fill_provider_form(self, query: DrugPriorAuthQuery) -> None:
        """
        Fill the provider information form and select a provider from search results.

        Args:
            query: DrugPriorAuthQuery with provider information

        Raises:
            ValidationError: If required fields missing
            PortalChangedError: If form filling fails
        """
        try:
            logger.info("Filling provider form...")

            # Ensure form is loaded
            if not self.is_on_provider_form():
                raise PortalChangedError("Provider form not found - may not be on correct page")

            # Fill Provider NPI (required)
            if not query.provider_npi:
                raise ValidationError("Provider NPI is required")
            
            logger.info(f"Filling Provider NPI: {query.provider_npi}")
            npi_input = self.wait_for_visible(self.PROVIDER_NPI_INPUT, timeout=5)
            npi_input.clear()
            npi_input.send_keys(query.provider_npi)
            time.sleep(0.5)

            # Click "Retrieve Provider Info" button
            try:
                retrieve_button = self.wait_for_clickable(
                    self.RETRIEVE_PROVIDER_INFO_BUTTON, timeout=5
                )
                logger.info("Clicking 'Retrieve Provider Info' button...")
                retrieve_button.click()
                
                # Wait for search results to appear
                logger.info("Waiting for provider search results...")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(self.PROVIDER_RESULT_ROWS)
                )
                time.sleep(1)  # Additional wait for results to fully render
                logger.info("Provider search results loaded")
            except Exception as e:
                logger.error(f"Failed to retrieve provider info: {e}")
                raise PortalChangedError(f"Failed to retrieve provider info: {e}") from e

            # Select a provider from the results
            self.select_provider_from_results(query)

            logger.info("Provider form filled and provider selected successfully")

        except (ValidationError, PortalChangedError):
            raise
        except Exception as e:
            logger.error(f"Failed to fill provider form: {e}")
            raise PortalChangedError(f"Failed to fill provider form: {e}") from e

    def select_provider_from_results(self, query: DrugPriorAuthQuery) -> None:
        """
        Select a provider from the search results table.

        Matches by provider name and/or address if provided, otherwise selects first result.

        Args:
            query: DrugPriorAuthQuery with provider information for matching

        Raises:
            PortalChangedError: If no provider found or selection fails
        """
        try:
            logger.info("Selecting provider from search results...")

            # Find all provider result rows
            result_rows = self.driver.find_elements(*self.PROVIDER_RESULT_ROWS)
            
            if not result_rows:
                raise PortalChangedError("No provider results found in search results")

            logger.info(f"Found {len(result_rows)} provider result(s)")

            # Try to find matching provider
            selected_provider = None
            match_found = False

            if query.provider_name or query.provider_address:
                # Try to match by name and/or address
                for row in result_rows:
                    try:
                        # Get provider info from the row
                        row_text = row.text
                        logger.debug(f"Checking provider row: {row_text[:100]}...")

                        # Check if name matches (if provided)
                        name_match = True
                        if query.provider_name:
                            name_match = query.provider_name.upper() in row_text.upper()
                        
                        # Check if address matches (if provided)
                        address_match = True
                        if query.provider_address:
                            address_match = query.provider_address.upper() in row_text.upper()
                        
                        # If both match (or only one is provided and it matches), select this provider
                        if name_match and address_match:
                            selected_provider = row
                            match_found = True
                            logger.info(f"Found matching provider: {row_text[:100]}...")
                            break
                    except Exception as e:
                        logger.debug(f"Error checking provider row: {e}")
                        continue

            # If no match found or no matching criteria provided, select first result
            if not match_found:
                logger.info("No specific match found or no matching criteria provided - selecting first result")
                selected_provider = result_rows[0]
                row_text = selected_provider.text
                logger.info(f"Selecting first provider: {row_text[:100]}...")

            if selected_provider is None:
                raise PortalChangedError("Could not select a provider from results")

            # Find and click the Select button in the selected row
            try:
                # The Select button should be in the same row
                select_button = selected_provider.find_element(*self.PROVIDER_SELECT_BUTTON)
                logger.info("Clicking Select button for chosen provider...")
                select_button.click()
                time.sleep(1)  # Wait for selection to register
                logger.info("Provider selected successfully")
            except Exception as e:
                logger.error(f"Could not find or click Select button: {e}")
                # Try alternative: click anywhere on the row
                try:
                    logger.info("Trying to click on the row itself...")
                    selected_provider.click()
                    time.sleep(1)
                    logger.info("Provider selected by clicking row")
                except Exception as e2:
                    raise PortalChangedError(
                        f"Could not select provider - Select button not found: {e}, {e2}"
                    ) from e2

        except PortalChangedError:
            raise
        except Exception as e:
            logger.error(f"Failed to select provider from results: {e}")
            raise PortalChangedError(f"Failed to select provider from results: {e}") from e

    def wait_for_provider_form(self, timeout: int = 30) -> None:
        """
        Wait for the provider form to load after clicking Novologix.

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            PortalChangedError: If form doesn't load
        """
        try:
            logger.info("Waiting for provider form to load...")
            initial_url = self.driver.current_url
            
            # Wait for Provider NPI field to appear
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self.PROVIDER_NPI_INPUT)
            )
            time.sleep(2)  # Additional wait for form to fully render
            logger.info("Provider form loaded successfully")

        except Exception as e:
            logger.error(f"Provider form did not load: {e}")
            raise PortalChangedError(f"Provider form did not load: {e}") from e

    def is_on_agreement_page(self) -> bool:
        """
        Check if currently on the agreement/redirection page (after selecting provider).

        Returns:
            True if on agreement page, False otherwise
        """
        try:
            # Check for the agreement text or Proceed button
            return (
                self.exists(self.AGREEMENT_PAGE_TEXT, timeout=3)
                or self.exists(self.PROCEED_TO_NOVOLOGIX_BUTTON, timeout=3)
            )
        except:
            return False

    def click_proceed_to_novologix(self) -> None:
        """
        Click the "Proceed to Novologix" button on the agreement page.

        Raises:
            PortalChangedError: If button not found or click fails
        """
        try:
            logger.info("Clicking 'Proceed to Novologix' button...")

            # Try XPath first (more reliable for text matching)
            try:
                proceed_button = self.wait_for_clickable(
                    self.PROCEED_TO_NOVOLOGIX_BUTTON, timeout=5
                )
                proceed_button.click()
            except:
                # Fallback to CSS selector
                proceed_button = self.wait_for_clickable(
                    self.PROCEED_BUTTON_ALT, timeout=5
                )
                proceed_button.click()

            logger.info("Proceed to Novologix button clicked successfully")
            time.sleep(3)  # Wait for navigation/redirection

        except Exception as e:
            logger.error(f"Failed to click Proceed to Novologix button: {e}")
            raise PortalChangedError(
                f"Failed to click Proceed to Novologix button: {e}"
            ) from e

    def wait_for_novologix_form(self, timeout: int = 30) -> None:
        """
        Wait for the Novologix form to load after clicking Proceed.

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            PortalChangedError: If form doesn't load
        """
        try:
            logger.info("Waiting for Novologix form to load...")
            
            # Wait for URL to change or form elements to appear
            # The form might be in an iframe or on a new page
            initial_url = self.driver.current_url
            
            # Wait for either URL change or form elements
            WebDriverWait(self.driver, timeout).until(
                lambda d: (
                    d.current_url != initial_url
                    or len(d.find_elements(By.CSS_SELECTOR, "input, select, textarea, form")) > 0
                )
            )
            
            # Check if form is in an iframe
            from selenium.webdriver.common.by import By as ByLocator
            iframes = self.driver.find_elements(ByLocator.TAG_NAME, "iframe")
            if iframes:
                logger.info(f"Found {len(iframes)} iframe(s), may need to switch to iframe for form")
                # Don't switch automatically - let the form filling method handle it
            
            time.sleep(2)  # Additional wait for form to fully render
            logger.info("Novologix form loaded (or page redirected)")

        except Exception as e:
            logger.error(f"Novologix form did not load: {e}")
            raise PortalChangedError(f"Novologix form did not load: {e}") from e