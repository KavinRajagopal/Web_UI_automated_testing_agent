"""
ProductsPage - Page Object for the Products/Inventory page
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from typing import List, Optional
from pages.base_page import BasePage


class ProductsPage(BasePage):
    """Page Object for the Products/Inventory page after login."""

    # Locators
    PAGE_TITLE = (By.CSS_SELECTOR, "[data-test='title']")
    INVENTORY_CONTAINER = (By.CSS_SELECTOR, "[data-test='inventory-container']")
    INVENTORY_LIST = (By.CSS_SELECTOR, "[data-test='inventory-list']")
    INVENTORY_ITEMS = (By.CSS_SELECTOR, "[data-test='inventory-item']")
    PRODUCT_NAMES = (By.CSS_SELECTOR, "[data-test='inventory-item-name']")
    PRODUCT_PRICES = (By.CSS_SELECTOR, "[data-test='inventory-item-price']")
    SORT_DROPDOWN = (By.CSS_SELECTOR, "[data-test='product-sort-container']")
    SHOPPING_CART_LINK = (By.CSS_SELECTOR, "[data-test='shopping-cart-link']")
    SHOPPING_CART_BADGE = (By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")
    BURGER_MENU_BUTTON = (By.ID, "react-burger-menu-btn")
    ERROR_MESSAGE = (By.CSS_SELECTOR, "[data-test='error']")
    
    # Add to cart button pattern - will be formatted with product name
    ADD_TO_CART_BUTTON_TEMPLATE = "[data-test='add-to-cart-{product_id}']"

    def __init__(self, driver):
        """
        Initialize ProductsPage.
        
        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    # Element Getters
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
        self.find_element_visible(*self.INVENTORY_ITEMS)
        return self.driver.find_elements(*self.INVENTORY_ITEMS)

    def get_product_name_elements(self) -> List[WebElement]:
        """
        Get all product name elements.
        
        Returns:
            List[WebElement]: List of product name elements
        """
        self.find_element_visible(*self.PRODUCT_NAMES)
        return self.driver.find_elements(*self.PRODUCT_NAMES)

    def get_product_price_elements(self) -> List[WebElement]:
        """
        Get all product price elements.
        
        Returns:
            List[WebElement]: List of product price elements
        """
        self.find_element_visible(*self.PRODUCT_PRICES)
        return self.driver.find_elements(*self.PRODUCT_PRICES)

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

    def get_shopping_cart_badge_element(self) -> Optional[WebElement]:
        """
        Get the shopping cart badge element if present.
        
        Returns:
            WebElement or None: The cart badge element if present, None otherwise
        """
        if self.is_element_present(*self.SHOPPING_CART_BADGE):
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
        Check if currently on the products page.
        
        Returns:
            bool: True if on products page, False otherwise
        """
        try:
            title_element = self.get_page_title_element()
            return title_element.text.upper() == "PRODUCTS"
        except Exception:
            return False

    def is_inventory_container_visible(self) -> bool:
        """
        Check if the inventory container is visible.
        
        Returns:
            bool: True if inventory container is visible, False otherwise
        """
        return self.is_element_present(*self.INVENTORY_CONTAINER)

    def get_page_title(self) -> str:
        """
        Get the page title text.
        
        Returns:
            str: The page title text
        """
        return self.get_element_text(*self.PAGE_TITLE)

    def get_all_product_names(self) -> List[str]:
        """
        Get all product names displayed on the page.
        
        Returns:
            List[str]: List of product names
        """
        name_elements = self.get_product_name_elements()
        return [element.text for element in name_elements]

    def get_all_product_prices(self) -> List[str]:
        """
        Get all product prices displayed on the page.
        
        Returns:
            List[str]: List of product prices (including $ symbol)
        """
        price_elements = self.get_product_price_elements()
        return [element.text for element in price_elements]

    def get_product_count(self) -> int:
        """
        Get the count of products displayed on the page.
        
        Returns:
            int: Number of products displayed
        """
        items = self.get_inventory_items()
        return len(items)

    def is_inventory_displayed(self) -> bool:
        """
        Check if the inventory/products list is displayed.
        
        Returns:
            bool: True if inventory is displayed, False otherwise
        """
        return self.is_element_present(*self.INVENTORY_CONTAINER)

    def select_sort_option(self, option_value: str) -> None:
        """
        Select a sort option from the dropdown.
        
        Args:
            option_value: The value of the sort option to select
                         Options: 'az', 'za', 'lohi', 'hilo'
        """
        from selenium.webdriver.support.ui import Select
        
        dropdown = self.get_sort_dropdown()
        select = Select(dropdown)
        select.select_by_value(option_value)

    def get_active_sort_option(self) -> str:
        """
        Get the currently active sort option.
        
        Returns:
            str: The value of the currently selected sort option
        """
        from selenium.webdriver.support.ui import Select
        
        dropdown = self.get_sort_dropdown()
        select = Select(dropdown)
        return select.first_selected_option.get_attribute("value")

    def add_product_to_cart(self, product_name: str) -> None:
        """
        Add a product to the cart by its name.
        
        Args:
            product_name: The name of the product to add
                         e.g., 'Sauce Labs Backpack' -> 'sauce-labs-backpack'
        """
        # Convert product name to the format used in data-test attribute
        product_id = product_name.lower().replace(" ", "-")
        add_button_selector = self.ADD_TO_CART_BUTTON_TEMPLATE.format(product_id=product_id)
        add_button_locator = (By.CSS_SELECTOR, add_button_selector)
        
        self.click(*add_button_locator)

    def get_cart_badge_count(self) -> int:
        """
        Get the number displayed on the cart badge.
        
        Returns:
            int: The number of items in cart, 0 if badge not present
        """
        badge = self.get_shopping_cart_badge_element()
        if badge:
            try:
                return int(badge.text)
            except ValueError:
                return 0
        return 0

    def click_shopping_cart(self) -> None:
        """
        Click the shopping cart link to navigate to cart page.
        """
        self.click(*self.SHOPPING_CART_LINK)

    def open_burger_menu(self) -> None:
        """
        Open the burger/hamburger menu.
        """
        self.click(*self.BURGER_MENU_BUTTON)

    # Additional helper methods
    def is_page_loaded(self) -> bool:
        """
        Check if the products page is fully loaded.
        
        Returns:
            bool: True if page is loaded, False otherwise
        """
        return self.is_on_products_page() and self.is_inventory_displayed()

    def is_title_displayed(self) -> bool:
        """
        Check if the page title is displayed.
        
        Returns:
            bool: True if title is displayed, False otherwise
        """
        return self.is_element_present(*self.PAGE_TITLE)

    def get_title_text(self) -> str:
        """
        Get the title text (alias for get_page_title).
        
        Returns:
            str: The page title text
        """
        return self.get_page_title()

    def is_on_page(self) -> bool:
        """
        Check if on the products page (alias for is_on_products_page).
        
        Returns:
            bool: True if on products page, False otherwise
        """
        return self.is_on_products_page()

    def get_product_by_name(self, product_name: str) -> Optional[WebElement]:
        """
        Get a product item element by its name.
        
        Args:
            product_name: The name of the product to find
            
        Returns:
            WebElement or None: The product item element if found
        """
        items = self.get_inventory_items()
        for item in items:
            name_element = item.find_element(*self.PRODUCT_NAMES)
            if name_element.text == product_name:
                return item
        return None

    def get_product_price_by_name(self, product_name: str) -> Optional[str]:
        """
        Get the price of a specific product by name.
        
        Args:
            product_name: The name of the product
            
        Returns:
            str or None: The product price if found
        """
        product = self.get_product_by_name(product_name)
        if product:
            price_element = product.find_element(By.CSS_SELECTOR, "[data-test='inventory-item-price']")
            return price_element.text
        return None

    def is_error_displayed(self) -> bool:
        """
        Check if an error message is displayed on the page.
        
        Returns:
            bool: True if error is displayed, False otherwise
        """
        return self.is_element_present(*self.ERROR_MESSAGE)

    def get_error_message(self) -> str:
        """
        Get the error message text if displayed.
        
        Returns:
            str: The error message text, empty string if not present
        """
        if self.is_error_displayed():
            return self.get_element_text(*self.ERROR_MESSAGE)
        return ""