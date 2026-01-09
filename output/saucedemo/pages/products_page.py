"""
Products Page Object Model for Sauce Demo application.
Uses Selenium WebDriver for browser automation.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from typing import List, Optional
from pages.base_page import BasePage


class ProductsPage(BasePage):
    """Page Object for the Products/Inventory page."""

    # Page URL
    PAGE_URL = "/inventory.html"

    # Locators - defined as class attributes using tuples
    PAGE_TITLE = (By.CSS_SELECTOR, "[data-test='title']")
    INVENTORY_CONTAINER = (By.CSS_SELECTOR, "[data-test='inventory-container']")
    INVENTORY_LIST = (By.CSS_SELECTOR, "[data-test='inventory-list']")
    INVENTORY_ITEM = (By.CSS_SELECTOR, "[data-test='inventory-item']")
    PRODUCT_NAME = (By.CSS_SELECTOR, "[data-test='inventory-item-name']")
    PRODUCT_PRICE = (By.CSS_SELECTOR, "[data-test='inventory-item-price']")
    PRODUCT_DESCRIPTION = (By.CSS_SELECTOR, "[data-test='inventory-item-desc']")
    SORT_DROPDOWN = (By.CSS_SELECTOR, "[data-test='product-sort-container']")
    ACTIVE_SORT_OPTION = (By.CSS_SELECTOR, "[data-test='active-option']")
    SHOPPING_CART_LINK = (By.CSS_SELECTOR, "[data-test='shopping-cart-link']")
    SHOPPING_CART_BADGE = (By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")
    BURGER_MENU_BUTTON = (By.ID, "react-burger-menu-btn")
    ADD_TO_CART_BUTTON_TEMPLATE = "[data-test='add-to-cart-{product_id}']"
    REMOVE_BUTTON_TEMPLATE = "[data-test='remove-{product_id}']"

    # Locator mapping for is_element_visible method
    LOCATOR_MAP = {
        "inventory_container": INVENTORY_CONTAINER,
        "page_title": PAGE_TITLE,
        "inventory_list": INVENTORY_LIST,
        "inventory_item": INVENTORY_ITEM,
        "product_name": PRODUCT_NAME,
        "product_price": PRODUCT_PRICE,
        "sort_dropdown": SORT_DROPDOWN,
        "shopping_cart_link": SHOPPING_CART_LINK,
        "shopping_cart_badge": SHOPPING_CART_BADGE,
        "burger_menu_button": BURGER_MENU_BUTTON,
    }

    def __init__(self, driver):
        """
        Initialize the ProductsPage.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def is_element_visible(self, element_name: str) -> bool:
        """
        Check if an element is visible by its name.

        Args:
            element_name: The name of the element to check (e.g., 'inventory_container')

        Returns:
            bool: True if the element is visible, False otherwise
        """
        locator = self.LOCATOR_MAP.get(element_name)
        if locator:
            return self.is_element_present(*locator)
        return False

    # Element Getter Methods
    def get_page_title_element(self) -> WebElement:
        """
        Get the page title element.

        Returns:
            WebElement: The page title element
        """
        return self.find_element_visible(*self.PAGE_TITLE)

    def get_inventory_container(self) -> WebElement:
        """
        Get the inventory container element.

        Returns:
            WebElement: The inventory container element
        """
        return self.find_element_visible(*self.INVENTORY_CONTAINER)

    def get_inventory_list(self) -> WebElement:
        """
        Get the inventory list element.

        Returns:
            WebElement: The inventory list element
        """
        return self.find_element_visible(*self.INVENTORY_LIST)

    def get_inventory_items(self) -> List[WebElement]:
        """
        Get all inventory item elements.

        Returns:
            List[WebElement]: List of inventory item elements
        """
        self.find_element_visible(*self.INVENTORY_ITEM)
        return self.driver.find_elements(*self.INVENTORY_ITEM)

    def get_product_name_elements(self) -> List[WebElement]:
        """
        Get all product name elements.

        Returns:
            List[WebElement]: List of product name elements
        """
        self.find_element_visible(*self.PRODUCT_NAME)
        return self.driver.find_elements(*self.PRODUCT_NAME)

    def get_product_price_elements(self) -> List[WebElement]:
        """
        Get all product price elements.

        Returns:
            List[WebElement]: List of product price elements
        """
        self.find_element_visible(*self.PRODUCT_PRICE)
        return self.driver.find_elements(*self.PRODUCT_PRICE)

    def get_sort_dropdown(self) -> WebElement:
        """
        Get the sort dropdown element.

        Returns:
            WebElement: The sort dropdown element
        """
        return self.find_element_clickable(*self.SORT_DROPDOWN)

    def get_shopping_cart_link(self) -> WebElement:
        """
        Get the shopping cart link element.

        Returns:
            WebElement: The shopping cart link element
        """
        return self.find_element_clickable(*self.SHOPPING_CART_LINK)

    def get_shopping_cart_badge(self) -> Optional[WebElement]:
        """
        Get the shopping cart badge element if present.

        Returns:
            Optional[WebElement]: The cart badge element or None if not present
        """
        if self.is_element_present(*self.SHOPPING_CART_BADGE, timeout=2):
            return self.find_element(*self.SHOPPING_CART_BADGE)
        return None

    def get_burger_menu_button(self) -> WebElement:
        """
        Get the burger menu button element.

        Returns:
            WebElement: The burger menu button element
        """
        return self.find_element_clickable(*self.BURGER_MENU_BUTTON)

    # Action Methods
    def is_on_products_page(self) -> bool:
        """
        Check if the user is on the products page.

        Returns:
            bool: True if on products page, False otherwise
        """
        return (self.PAGE_URL in self.driver.current_url and 
                self.is_element_present(*self.INVENTORY_CONTAINER))

    def is_on_page(self) -> bool:
        """
        Check if the user is on the products page.

        Returns:
            bool: True if on products page, False otherwise
        """
        return self.is_on_products_page()

    def get_page_title(self) -> str:
        """
        Get the page title text.

        Returns:
            str: The page title text
        """
        return self.get_element_text(*self.PAGE_TITLE)

    def is_inventory_displayed(self) -> bool:
        """
        Check if the inventory container is displayed.

        Returns:
            bool: True if inventory is displayed, False otherwise
        """
        return self.is_element_present(*self.INVENTORY_CONTAINER)

    def get_all_product_names(self) -> List[str]:
        """
        Get all product names from the inventory.

        Returns:
            List[str]: List of product names
        """
        name_elements = self.get_product_name_elements()
        return [element.text for element in name_elements]

    def get_all_product_prices(self) -> List[float]:
        """
        Get all product prices from the inventory.

        Returns:
            List[float]: List of product prices as floats
        """
        price_elements = self.get_product_price_elements()
        prices = []
        for element in price_elements:
            price_text = element.text.replace("$", "")
            prices.append(float(price_text))
        return prices

    def get_product_count(self) -> int:
        """
        Get the total number of products displayed.

        Returns:
            int: Number of products
        """
        items = self.get_inventory_items()
        return len(items)

    def sort_products_by(self, sort_option: str) -> None:
        """
        Sort products by the specified option.

        Args:
            sort_option: Sort option value (az, za, lohi, hilo)
        """
        from selenium.webdriver.support.ui import Select
        
        dropdown = self.get_sort_dropdown()
        select = Select(dropdown)
        select.select_by_value(sort_option)

    def get_active_sort_option(self) -> str:
        """
        Get the currently active sort option.

        Returns:
            str: The active sort option text
        """
        return self.get_element_text(*self.ACTIVE_SORT_OPTION)

    def _get_product_id_from_name(self, product_name: str) -> str:
        """
        Convert product name to product ID format used in data-test attributes.

        Args:
            product_name: The product name

        Returns:
            str: The product ID for use in selectors
        """
        return product_name.lower().replace(" ", "-")

    def add_product_to_cart(self, product_name: str) -> None:
        """
        Add a product to the cart by its name.

        Args:
            product_name: The name of the product to add
        """
        product_id = self._get_product_id_from_name(product_name)
        selector = self.ADD_TO_CART_BUTTON_TEMPLATE.format(product_id=product_id)
        self.click(By.CSS_SELECTOR, selector)

    def remove_product_from_cart(self, product_name: str) -> None:
        """
        Remove a product from the cart by its name.

        Args:
            product_name: The name of the product to remove
        """
        product_id = self._get_product_id_from_name(product_name)
        selector = self.REMOVE_BUTTON_TEMPLATE.format(product_id=product_id)
        self.click(By.CSS_SELECTOR, selector)

    def get_cart_badge_count(self) -> int:
        """
        Get the number displayed on the cart badge.

        Returns:
            int: The cart badge count, 0 if badge is not present
        """
        badge = self.get_shopping_cart_badge()
        if badge:
            return int(badge.text)
        return 0

    def click_shopping_cart(self) -> None:
        """Click the shopping cart link to navigate to the cart page."""
        self.click(*self.SHOPPING_CART_LINK)

    def open_burger_menu(self) -> None:
        """Open the burger menu."""
        self.click(*self.BURGER_MENU_BUTTON)

    def are_products_sorted_az(self) -> bool:
        """
        Check if products are sorted alphabetically A to Z.

        Returns:
            bool: True if sorted A-Z, False otherwise
        """
        names = self.get_all_product_names()
        return names == sorted(names)

    def are_products_sorted_za(self) -> bool:
        """
        Check if products are sorted alphabetically Z to A.

        Returns:
            bool: True if sorted Z-A, False otherwise
        """
        names = self.get_all_product_names()
        return names == sorted(names, reverse=True)

    def are_products_sorted_price_low_high(self) -> bool:
        """
        Check if products are sorted by price low to high.

        Returns:
            bool: True if sorted low to high, False otherwise
        """
        prices = self.get_all_product_prices()
        return prices == sorted(prices)

    def are_products_sorted_price_high_low(self) -> bool:
        """
        Check if products are sorted by price high to low.

        Returns:
            bool: True if sorted high to low, False otherwise
        """
        prices = self.get_all_product_prices()
        return prices == sorted(prices, reverse=True)

    def is_page_loaded(self) -> bool:
        """
        Check if the products page is fully loaded.

        Returns:
            bool: True if page is loaded, False otherwise
        """
        return (self.is_element_present(*self.PAGE_TITLE) and 
                self.is_element_present(*self.INVENTORY_CONTAINER))

    def is_title_displayed(self) -> bool:
        """
        Check if the page title is displayed.

        Returns:
            bool: True if title is displayed, False otherwise
        """
        return self.is_element_present(*self.PAGE_TITLE)

    def get_title_text(self) -> str:
        """
        Get the page title text.

        Returns:
            str: The page title text
        """
        return self.get_page_title()