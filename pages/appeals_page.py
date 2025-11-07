"""Appeals page object for form filling and result parsing."""

import time
from typing import Optional

from loguru import logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from core.errors import PortalBusinessError, PortalChangedError, ValidationError
from domain.appeals_models import AppealsQuery, AppealsResult

from .base_page import BasePage


class AppealsPage(BasePage):
    """Page object for Availity appeals worklist form and results."""

    # Form fields - based on provided placeholders
    SEARCH_BY_DROPDOWN = (By.ID, "searchBy")  # React Select dropdown for search criteria
    SEARCH_TERM_INPUT = (By.ID, "search-input")  # Search term input field
    SEARCH_BUTTON = (By.ID, "search-button")  # Search submit button

    # Alternative selectors (fallbacks)
    SEARCH_BY_INPUT = (By.CSS_SELECTOR, "input#searchBy, input.searchBy__input")  # React Select input
    SEARCH_TERM_INPUT_ALT = (By.NAME, "searchTerm")  # Alternative by name attribute

    # Results section - TODO: Update based on actual results page structure
    RESULTS_CONTAINER = (By.CSS_SELECTOR, "div[class*='result'], table, .card, [class*='appeal'], [class*='worklist']")
    RESULTS_GRID = (By.CSS_SELECTOR, "table, [class*='grid'], [class*='table']")
    RESULTS_ROWS = (By.CSS_SELECTOR, "tbody tr, [class*='row']")

    # Error messages
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".error-message, .alert-danger, [role='alert'], [class*='error']")
    NO_RESULTS_MESSAGE = (By.XPATH, "//*[contains(text(), 'could not find') or contains(text(), 'no results') or contains(text(), 'no appeals')]")

    def __init__(self, driver: WebDriver):
        """
        Initialize appeals page.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def ensure_loaded(self) -> None:
        """
        Ensure the appeals form is loaded.

        Raises:
            PortalChangedError: If form elements not found
        """
        try:
            logger.info("Waiting for appeals form to load...")
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
                    logger.debug(f"Attempt {attempt + 1}/{max_attempts} to find search form...")
                    # Try to find search by dropdown
                    try:
                        self.wait_for_visible(self.SEARCH_BY_DROPDOWN, timeout=5)
                        logger.info("Found search by dropdown by ID!")
                        break
                    except:
                        # Try alternative selector
                        try:
                            self.wait_for_visible(self.SEARCH_BY_INPUT, timeout=3)
                            logger.info("Found search by input by CSS!")
                            break
                        except:
                            # Try search term input
                            try:
                                self.wait_for_visible(self.SEARCH_TERM_INPUT, timeout=3)
                                logger.info("Found search term input - form is loaded!")
                                break
                            except:
                                # Try search button
                                try:
                                    self.wait_for_visible(self.SEARCH_BUTTON, timeout=3)
                                    logger.info("Found search button - form is loaded!")
                                    break
                                except:
                                    pass
                except Exception as e:
                    if attempt == max_attempts - 1:
                        # Last attempt - try to find ANY input field
                        try:
                            self.wait_for_visible((ByLocator.CSS_SELECTOR, "input, textarea"), timeout=3)
                            logger.info("Found some form input - form is loaded!")
                            break
                        except:
                            raise PortalChangedError(
                                f"Appeals form not found after {max_attempts} attempts. Current URL: {self.driver.current_url}"
                            )
                    else:
                        logger.debug(f"Waiting 1 second before retry...")
                        time.sleep(1)

            logger.info("Appeals form loaded successfully!")

        except Exception as e:
            logger.error(f"Appeals form not loaded. Current URL: {self.driver.current_url}")
            logger.error("Taking screenshot for debugging...")
            raise PortalChangedError(f"Appeals form not loaded: {e}") from e

    def select_search_by(self, search_by: str) -> None:
        """
        Select search criteria from React Select dropdown.

        Args:
            search_by: Search criteria type (e.g., "Claim Number", "Member ID")

        Raises:
            PortalChangedError: If search by selection fails
        """
        try:
            logger.info(f"Selecting search by: {search_by}")

            # Try multiple selectors to find the search by dropdown
            search_by_input = None
            from selenium.webdriver.common.by import By as ByLocator

            # Try by ID first
            try:
                search_by_input = self.wait_for_clickable(self.SEARCH_BY_DROPDOWN, timeout=5)
                logger.debug("Found search by dropdown by ID")
            except:
                # Try alternative CSS selector
                try:
                    search_by_input = self.wait_for_clickable(self.SEARCH_BY_INPUT, timeout=5)
                    logger.debug("Found search by input by CSS selector")
                except:
                    raise PortalChangedError("Could not find search by dropdown with any selector")

            if search_by_input is None:
                raise PortalChangedError("Search by dropdown element not found")

            # Clear any existing selection first
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Clear the field completely using Ctrl+A and Delete
            search_by_input.click()
            time.sleep(0.3)
            search_by_input.send_keys(Keys.CONTROL + "a")
            search_by_input.send_keys(Keys.DELETE)
            time.sleep(0.3)

            # Now click to open the dropdown
            search_by_input.click()

            # Wait for dropdown to open
            try:
                WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                    lambda d: search_by_input.get_attribute("aria-expanded") == "true"
                )
            except:
                time.sleep(0.5)

            # Type the search by value to search/filter
            search_by_input.send_keys(search_by)

            # Wait for results to appear
            try:
                WebDriverWait(self.driver, 3, poll_frequency=0.2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='option'], [id*='option']"))
                )
            except:
                time.sleep(0.5)

            # Press Enter to select the first/best match
            search_by_input.send_keys(Keys.ENTER)

            # Wait for selection to complete
            try:
                WebDriverWait(self.driver, 2, poll_frequency=0.2).until(
                    lambda d: search_by_input.get_attribute("aria-expanded") != "true"
                )
            except:
                time.sleep(0.5)

            # Verify selection
            time.sleep(0.5)
            selected_value = search_by_input.get_attribute("value")
            logger.info(f"Search by selected - field shows: {selected_value}")

        except Exception as e:
            raise PortalChangedError(f"Failed to select search by: {e}") from e

    def fill_search_form(self, query: AppealsQuery) -> None:
        """
        Fill the appeals search form.

        Args:
            query: AppealsQuery with form data

        Raises:
            ValidationError: If required fields are missing
            PortalChangedError: If form elements not found
        """
        try:
            logger.info(f"Filling appeals form for request ID: {query.request_id}")

            # Validate required fields
            if not query.search_by:
                raise ValidationError("search_by is required")
            if not query.search_term:
                raise ValidationError("search_term is required")

            # Select search by using React Select
            self.select_search_by(query.search_by)

            # Wait for form to update after search by selection
            time.sleep(1)

            # Fill search term
            try:
                # Try primary selector first
                if self.exists(self.SEARCH_TERM_INPUT, timeout=3):
                    self.type(self.SEARCH_TERM_INPUT, query.search_term, clear_first=True)
                    logger.debug(f"Search term: {query.search_term}")
                elif self.exists(self.SEARCH_TERM_INPUT_ALT, timeout=3):
                    self.type(self.SEARCH_TERM_INPUT_ALT, query.search_term, clear_first=True)
                    logger.debug(f"Search term (alt): {query.search_term}")
                else:
                    raise PortalChangedError("Could not find search term input field")
            except Exception as e:
                logger.error(f"Failed to fill search term: {e}")
                raise PortalChangedError(f"Failed to fill search term: {e}") from e

            logger.info("Form filled successfully")

        except (ValidationError, PortalChangedError):
            raise
        except Exception as e:
            logger.error(f"Failed to fill form: {e}")
            raise PortalChangedError(f"Form filling failed: {e}") from e

    def submit_and_wait(self, timeout: int = 60) -> None:
        """
        Submit the appeals search form and wait for results.

        Args:
            timeout: Maximum wait time in seconds

        Raises:
            PortalBusinessError: If portal returns a business error
            PortalChangedError: If results don't load
        """
        try:
            logger.info("Submitting appeals search form")

            # Find and click search button
            submit_button = self.wait_for_clickable(self.SEARCH_BUTTON, timeout=5)

            # Wait until button is enabled
            from selenium.webdriver.support.ui import WebDriverWait
            wait = WebDriverWait(self.driver, 5, poll_frequency=0.2)
            wait.until(lambda d: submit_button.is_enabled())

            # Scroll into view
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button)

            # Click submit
            try:
                submit_button.click()
                logger.debug("Search button clicked")
            except Exception as e1:
                logger.warning(f"Regular click failed: {e1}, trying JavaScript click...")
                self.driver.execute_script("arguments[0].click();", submit_button)
                logger.debug("Search button clicked via JavaScript")

            # Wait for results to load
            logger.info("Waiting for appeals results to load...")
            time.sleep(5)  # Initial wait for page transition

            # Wait for any loading spinners to disappear
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By

            try:
                WebDriverWait(self.driver, 30, poll_frequency=1).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='loading'], [class*='spinner'], [class*='loader']"))
                )
                logger.debug("Loading indicators disappeared")
            except:
                logger.debug("No loading indicators found or timeout waiting for them")

            # Additional wait for results to fully render
            logger.info("Waiting additional time for results to fully render...")
            time.sleep(10)

            # Check for error messages first
            if self.exists(self.ERROR_MESSAGE, timeout=5):
                error_text = self.get_text(self.ERROR_MESSAGE)
                logger.warning(f"Portal returned error: {error_text}")
                raise PortalBusinessError(f"Portal error: {error_text}")

            # Check for "no results" message (this is not an error, just no results)
            if self.exists(self.NO_RESULTS_MESSAGE, timeout=5):
                logger.info("No results found message detected")

            # Wait for results container (may be empty results, table, or list)
            logger.info("Looking for results container...")
            try:
                # Try to find results container with longer timeout
                self.wait_for_visible(self.RESULTS_CONTAINER, timeout=30)
                logger.info("Results container loaded")
            except:
                # Results container might not appear if no results
                logger.info("Results container not found - may be no results or different structure")

            # Final wait to ensure everything is rendered
            logger.info("Final wait to ensure all content is rendered...")
            time.sleep(5)

        except PortalBusinessError:
            raise
        except Exception as e:
            logger.warning(f"Error waiting for results: {e}")
            # Don't raise - might be no results scenario

    def parse_result(self, query: AppealsQuery) -> AppealsResult:
        """
        Parse appeals search results from the page.

        Args:
            query: Original query

        Returns:
            AppealsResult object
        """
        logger.info("Parsing appeals results from page...")

        result = AppealsResult(
            request_id=query.request_id,
            appeals_found=0,
            appeals=[],
            raw_response_html_path=None,  # Will be set by bot if saving HTML
        )

        try:
            from selenium.webdriver.common.by import By

            # Try to find results table/grid
            logger.info("Looking for results table/grid...")
            if self.exists(self.RESULTS_GRID, timeout=5):
                logger.info("Found results grid/table, parsing...")
                rows = self.find_elements(self.RESULTS_ROWS, timeout=5)
                logger.info(f"Found {len(rows)} result rows")

                result.appeals_found = len(rows)

                # Parse each row
                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if not cells:
                            cells = row.find_elements(By.CSS_SELECTOR, "[class*='cell'], div")

                        cell_texts = [cell.text.strip() for cell in cells if cell.text.strip()]
                        logger.debug(f"Row data: {cell_texts}")

                        # Create appeal dict from row data
                        appeal = {}
                        for i, text in enumerate(cell_texts):
                            # Try to identify fields by content patterns
                            text_lower = text.lower()
                            if any(keyword in text_lower for keyword in ['appeal', 'id', 'number']):
                                appeal['appeal_id'] = text
                            elif any(keyword in text_lower for keyword in ['claim', 'number']):
                                appeal['claim_number'] = text
                            elif any(keyword in text_lower for keyword in ['status']):
                                appeal['status'] = text
                            elif any(keyword in text_lower for keyword in ['date', 'submitted']):
                                appeal['submitted_date'] = text
                            else:
                                # Store as generic field
                                appeal[f'field_{i}'] = text

                        if appeal:
                            result.appeals.append(appeal)
                    except Exception as e:
                        logger.warning(f"Error parsing row: {e}")

            # If no table found, try to find any result indicators
            if result.appeals_found == 0:
                logger.info("No table found, searching for other result indicators...")
                # Try to find any text that might indicate results
                page_text = self.driver.page_source.lower()
                if 'appeal' in page_text or 'result' in page_text:
                    # There might be results but in a different format
                    logger.info("Found appeal-related content on page")
                    result.appeals_found = 1  # At least something found
                    result.appeals.append({"note": "Results found but format not recognized"})

            logger.info(f"=== Parsing Summary ===")
            logger.info(f"Appeals Found: {result.appeals_found}")
            logger.info(f"Appeals: {len(result.appeals)}")
            logger.info("======================")

        except Exception as e:
            logger.warning(f"Error parsing results: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Return result with whatever we found

        logger.info(f"Completed parsing result for request {query.request_id}")
        return result

