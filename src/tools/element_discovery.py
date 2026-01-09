"""Element Discovery Tool - Automated extraction of UI selectors using Selenium.

This tool crawls web pages and extracts interactive UI elements with their
most stable selectors (id, data-testid, name, aria-label).

For demo: Focused on saucedemo.com which uses data-test attributes.
"""

import base64
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

from ..models.schemas import (
    PageMetadata,
    UIElement,
    ElementSelector,
    SelectorType
)

logger = logging.getLogger(__name__)


class ElementDiscoveryTool:
    """
    Automated element discovery using Selenium WebDriver.
    
    Extracts interactive UI elements and their selectors from web pages.
    Prioritizes stable selectors: id > data-testid > name > aria-label
    
    Usage:
        tool = ElementDiscoveryTool()
        tool.start_browser()
        page_metadata = tool.discover_page("https://www.saucedemo.com", "LoginPage")
        tool.close_browser()
    """
    
    # CSS selector for interactive elements
    INTERACTIVE_SELECTOR = (
        "input, button, a, select, textarea, "
        "[role='button'], [role='link'], [role='checkbox'], [role='radio'], "
        "[onclick], [data-test], [data-testid]"
    )
    
    # Selector priority (higher = better)
    SELECTOR_PRIORITY = {
        "id": 4,
        "data-test": 3,  # saucedemo uses data-test
        "data-testid": 3,
        "name": 2,
        "aria-label": 1,
    }
    
    def __init__(
        self,
        headless: bool = True,
        implicit_wait: int = 10,
        page_load_timeout: int = 30
    ):
        """
        Initialize the Element Discovery Tool.
        
        Args:
            headless: Run browser in headless mode (no GUI)
            implicit_wait: Implicit wait time for element lookups
            page_load_timeout: Max time to wait for page load
        """
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.page_load_timeout = page_load_timeout
        self.driver: Optional[WebDriver] = None
    
    def start_browser(self) -> WebDriver:
        """
        Initialize and start Chrome WebDriver.
        
        Uses webdriver-manager to automatically download and manage ChromeDriver.
        
        Returns:
            WebDriver instance
        """
        options = Options()
        
        if self.headless:
            options.add_argument("--headless=new")
        
        # Common Chrome options for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        
        # Suppress logging
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Use webdriver-manager to automatically get the correct ChromeDriver
        service = Service(ChromeDriverManager().install())
        
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(self.implicit_wait)
        self.driver.set_page_load_timeout(self.page_load_timeout)
        
        logger.info(f"Browser started (headless={self.headless})")
        return self.driver
    
    def close_browser(self):
        """Close the browser and cleanup."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Browser closed")
    
    def navigate(self, url: str, wait_for_load: bool = True) -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: Target URL
            wait_for_load: Wait for page to fully load
            
        Returns:
            True if navigation successful
        """
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        try:
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            if wait_for_load:
                # Wait for document ready state
                WebDriverWait(self.driver, self.page_load_timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            
            return True
            
        except TimeoutException:
            logger.error(f"Timeout navigating to {url}")
            return False
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False
    
    def take_screenshot(self) -> Optional[bytes]:
        """
        Take a screenshot of the current page.
        
        Returns:
            PNG image as bytes, or None if failed
        """
        if not self.driver:
            return None
        
        try:
            return self.driver.get_screenshot_as_png()
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    def take_screenshot_base64(self) -> Optional[str]:
        """
        Take a screenshot and return as base64 string.
        
        Returns:
            Base64-encoded PNG, or None if failed
        """
        png_bytes = self.take_screenshot()
        if png_bytes:
            return base64.b64encode(png_bytes).decode('utf-8')
        return None
    
    def _extract_element_attributes(self, element: WebElement) -> Dict[str, Optional[str]]:
        """
        Extract all relevant attributes from a WebElement.
        
        Args:
            element: Selenium WebElement
            
        Returns:
            Dict of attribute name -> value
        """
        attributes = {}
        
        # Standard attributes
        for attr in ["id", "name", "type", "placeholder", "aria-label", "role", 
                     "data-test", "data-testid", "class", "value", "href"]:
            try:
                val = element.get_attribute(attr)
                if val:
                    attributes[attr] = val
            except StaleElementReferenceException:
                break
        
        # Tag name
        try:
            attributes["tag"] = element.tag_name
        except:
            pass
        
        # Text content (limited)
        try:
            text = element.text
            if text:
                attributes["text"] = text[:100]  # Limit text length
        except:
            pass
        
        return attributes
    
    def _determine_element_type(self, attrs: Dict[str, Optional[str]]) -> str:
        """
        Determine the element type from attributes.
        
        Args:
            attrs: Element attributes dict
            
        Returns:
            Element type string (input, button, link, etc.)
        """
        tag = attrs.get("tag", "").lower()
        input_type = attrs.get("type", "").lower()
        role = attrs.get("role", "").lower()
        
        if tag == "input":
            if input_type in ["text", "email", "password", "tel", "search"]:
                return "input"
            elif input_type in ["submit", "button"]:
                return "button"
            elif input_type in ["checkbox"]:
                return "checkbox"
            elif input_type in ["radio"]:
                return "radio"
            return "input"
        elif tag == "button":
            return "button"
        elif tag == "a":
            return "link"
        elif tag == "select":
            return "select"
        elif tag == "textarea":
            return "textarea"
        elif role == "button":
            return "button"
        elif role in ["checkbox", "radio"]:
            return role
        
        return "element"
    
    def _generate_element_name(self, attrs: Dict[str, Optional[str]], index: int) -> str:
        """
        Generate a meaningful element name from attributes.
        
        Args:
            attrs: Element attributes dict
            index: Element index for fallback naming
            
        Returns:
            Element name string
        """
        # Priority order for naming
        name_sources = [
            attrs.get("data-test"),
            attrs.get("data-testid"),
            attrs.get("id"),
            attrs.get("name"),
            attrs.get("aria-label"),
            attrs.get("placeholder"),
        ]
        
        for source in name_sources:
            if source:
                # Clean up the name
                name = re.sub(r'[^a-zA-Z0-9_-]', '_', source)
                name = re.sub(r'_+', '_', name)
                name = name.strip('_').lower()
                if name:
                    return name
        
        # Fallback: use tag and type
        tag = attrs.get("tag", "element")
        el_type = attrs.get("type", "")
        text = attrs.get("text", "")[:20] if attrs.get("text") else ""
        
        if text:
            text_clean = re.sub(r'[^a-zA-Z0-9]', '_', text).lower()
            return f"{tag}_{text_clean}_{index}"
        
        return f"{tag}_{el_type}_{index}" if el_type else f"{tag}_{index}"
    
    def _build_selectors(self, attrs: Dict[str, Optional[str]]) -> List[ElementSelector]:
        """
        Build list of selectors for an element, ordered by stability.
        
        Args:
            attrs: Element attributes dict
            
        Returns:
            List of ElementSelector objects, best first
        """
        selectors = []
        
        # ID selector (most stable)
        if attrs.get("id"):
            # Check if it looks like a dynamic ID
            id_val = attrs["id"]
            is_stable = not bool(re.search(r'[_-]\d{3,}|__[a-zA-Z0-9]{5,}', id_val))
            
            selectors.append(ElementSelector(
                selector_type=SelectorType.ID,
                value=id_val,
                confidence=0.95 if is_stable else 0.5,
                is_stable=is_stable
            ))
        
        # data-test / data-testid (very stable - designed for testing)
        for attr_name in ["data-test", "data-testid"]:
            if attrs.get(attr_name):
                selectors.append(ElementSelector(
                    selector_type=SelectorType.DATA_TESTID,
                    value=attrs[attr_name],
                    confidence=0.98,
                    is_stable=True
                ))
                break  # Only add one
        
        # name attribute (stable)
        if attrs.get("name"):
            selectors.append(ElementSelector(
                selector_type=SelectorType.NAME,
                value=attrs["name"],
                confidence=0.9,
                is_stable=True
            ))
        
        # aria-label (stable but may change with localization)
        if attrs.get("aria-label"):
            selectors.append(ElementSelector(
                selector_type=SelectorType.ARIA_LABEL,
                value=attrs["aria-label"],
                confidence=0.85,
                is_stable=True
            ))
        
        # Sort by confidence (highest first)
        selectors.sort(key=lambda s: s.confidence, reverse=True)
        
        return selectors
    
    def _is_element_useful(self, attrs: Dict[str, Optional[str]]) -> bool:
        """
        Check if an element is worth including (has stable selectors).
        
        Args:
            attrs: Element attributes dict
            
        Returns:
            True if element should be included
        """
        # Must have at least one stable selector attribute
        stable_attrs = ["id", "data-test", "data-testid", "name", "aria-label"]
        return any(attrs.get(attr) for attr in stable_attrs)
    
    def discover_elements(self) -> List[UIElement]:
        """
        Discover all interactive elements on the current page.
        
        Returns:
            List of UIElement objects
        """
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        elements = []
        seen_selectors = set()  # Avoid duplicates
        
        try:
            # Find all interactive elements
            web_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                self.INTERACTIVE_SELECTOR
            )
            
            logger.info(f"Found {len(web_elements)} potential elements")
            
            for idx, web_el in enumerate(web_elements):
                try:
                    # Skip invisible elements
                    if not web_el.is_displayed():
                        continue
                    
                    # Extract attributes
                    attrs = self._extract_element_attributes(web_el)
                    
                    # Skip if no useful selectors
                    if not self._is_element_useful(attrs):
                        continue
                    
                    # Build selectors
                    selectors = self._build_selectors(attrs)
                    
                    if not selectors:
                        continue
                    
                    # Dedup by best selector
                    best_selector = selectors[0].value
                    if best_selector in seen_selectors:
                        continue
                    seen_selectors.add(best_selector)
                    
                    # Generate element name
                    name = self._generate_element_name(attrs, idx)
                    
                    # Determine element type
                    el_type = self._determine_element_type(attrs)
                    
                    # Build description
                    description = attrs.get("placeholder") or attrs.get("aria-label") or attrs.get("text") or f"{el_type} element"
                    
                    # Create UIElement
                    ui_element = UIElement(
                        name=name,
                        description=description[:200],
                        element_type=el_type,
                        selectors=selectors,
                        is_required=(el_type in ["input", "button", "submit"]),
                        wait_strategy="visible" if el_type == "input" else "clickable"
                    )
                    
                    elements.append(ui_element)
                    
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    logger.warning(f"Error processing element {idx}: {e}")
                    continue
            
            logger.info(f"Discovered {len(elements)} usable elements")
            
        except Exception as e:
            logger.error(f"Element discovery failed: {e}")
        
        return elements
    
    def discover_page(
        self,
        url: str,
        page_name: str,
        description: Optional[str] = None
    ) -> PageMetadata:
        """
        Discover elements on a page and return PageMetadata.
        
        Args:
            url: Page URL to navigate to
            page_name: Name for the page (e.g., "LoginPage")
            description: Optional page description
            
        Returns:
            PageMetadata object with discovered elements
        """
        if not self.driver:
            self.start_browser()
        
        # Navigate to page
        if not self.navigate(url):
            logger.error(f"Failed to navigate to {url}")
            return PageMetadata(
                page_name=page_name,
                page_url=url,
                description=description or f"Failed to load {url}",
                elements=[]
            )
        
        # Discover elements
        elements = self.discover_elements()
        
        # Build page metadata
        page_metadata = PageMetadata(
            page_name=page_name,
            page_url=url,
            description=description or f"Elements discovered from {url}",
            elements=elements,
            last_updated=datetime.now(),
            extracted_from=f"ElementDiscoveryTool - {datetime.now().isoformat()}"
        )
        
        logger.info(f"Page '{page_name}': discovered {len(elements)} elements")
        
        return page_metadata
    
    def discover_multiple_pages(
        self,
        pages: List[Dict[str, str]],
        login_action: Optional[callable] = None
    ) -> List[PageMetadata]:
        """
        Discover elements on multiple pages.
        
        Args:
            pages: List of dicts with 'url', 'name', 'description' keys
            login_action: Optional callable to perform login before accessing pages
            
        Returns:
            List of PageMetadata objects
        """
        if not self.driver:
            self.start_browser()
        
        results = []
        
        # Perform login if needed
        if login_action:
            try:
                login_action(self.driver)
                logger.info("Login action completed")
            except Exception as e:
                logger.error(f"Login action failed: {e}")
        
        for page_config in pages:
            url = page_config["url"]
            name = page_config["name"]
            description = page_config.get("description")
            
            page_metadata = self.discover_page(url, name, description)
            results.append(page_metadata)
        
        return results


# =============================================================================
# SAUCEDEMO-SPECIFIC HELPER
# =============================================================================

def create_saucedemo_discovery() -> ElementDiscoveryTool:
    """
    Create an ElementDiscoveryTool configured for saucedemo.com.
    
    Returns:
        Configured ElementDiscoveryTool
    """
    return ElementDiscoveryTool(headless=True)


def discover_saucedemo_pages() -> List[PageMetadata]:
    """
    Discover elements on all saucedemo.com pages.
    
    This is a convenience function for the demo that:
    1. Discovers login page (no auth required)
    2. Logs in with standard credentials
    3. Discovers products, cart, checkout pages
    
    Returns:
        List of PageMetadata for all discovered pages
    """
    tool = create_saucedemo_discovery()
    
    try:
        tool.start_browser()
        results = []
        
        # 1. Discover Login Page
        login_page = tool.discover_page(
            url="https://www.saucedemo.com",
            page_name="LoginPage",
            description="SauceDemo login page"
        )
        results.append(login_page)
        
        # 2. Log in
        driver = tool.driver
        driver.find_element(By.CSS_SELECTOR, "[data-test='username']").send_keys("standard_user")
        driver.find_element(By.CSS_SELECTOR, "[data-test='password']").send_keys("secret_sauce")
        driver.find_element(By.CSS_SELECTOR, "[data-test='login-button']").click()
        
        # Wait for products page
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='inventory-container']"))
        )
        
        # 3. Discover Products Page
        products_page = tool.discover_page(
            url=driver.current_url,
            page_name="ProductsPage",
            description="SauceDemo products/inventory page"
        )
        results.append(products_page)
        
        # 4. Add item to cart and go to cart
        add_to_cart_btn = driver.find_element(By.CSS_SELECTOR, "[data-test^='add-to-cart']")
        add_to_cart_btn.click()
        
        # Navigate to cart
        driver.find_element(By.CSS_SELECTOR, "[data-test='shopping-cart-link']").click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='cart-list']"))
        )
        
        # 5. Discover Cart Page
        cart_page = tool.discover_page(
            url=driver.current_url,
            page_name="CartPage",
            description="SauceDemo shopping cart page"
        )
        results.append(cart_page)
        
        # 6. Go to checkout
        driver.find_element(By.CSS_SELECTOR, "[data-test='checkout']").click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='firstName']"))
        )
        
        # 7. Discover Checkout Page
        checkout_page = tool.discover_page(
            url=driver.current_url,
            page_name="CheckoutPage",
            description="SauceDemo checkout information page"
        )
        results.append(checkout_page)
        
        return results
        
    finally:
        tool.close_browser()
