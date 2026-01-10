"""
ProductsPage - Page Object for Products/Inventory page
Uses Selenium WebDriver for browser automation
"""

from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from pages.base_page import BasePage


class ProductsPage(BasePage):
    """Page Object for the Products/Inventory page on SauceDemo"""

    # Locators
    PAGE_TITLE = (By.CSS_SELECTOR, "[data-test='title']")
    INVENTORY_CONTAINER = (By.CSS_SELECTOR, "[data-test='inventory-container']")
    INVENTORY_LIST = (By.CSS_SELECTOR, "[data-test='inventory-list']")
    INVENTORY_ITEM = (By.CSS_SELECTOR, "[data-test='inventory-item']")
    INVENTORY_ITEM_NAME = (By.CSS_SELECTOR, "[data-test='inventory-item-name']")
    INVENTORY_ITEM_PRICE = (By.CSS_SELECTOR, "[data-test='inventory-item-price']")
    INVENTORY_ITEM_DESC = (By.CSS_SELECTOR, "[data-test='inventory-item-desc']")
    SORT_DROPDOWN = (By.CSS_SELECTOR, "[data-test='product-sort-container']")
    SHOPPING_CART_LINK = (By.CSS_SELECTOR, "[data-test='shopping-cart-link']")
    SHOPPING_CART_BADGE = (By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")
    BURGER_MENU_BUTTON = (By.ID, "react-burger-menu-btn")
    ADD_TO_CART_BUTTON_TEMPLATE = "[data-test='add-to-cart-{product_id}']"
    REMOVE_BUTTON_TEMPLATE = "[data-test='remove-{product_id}']"

    def is_element_visible(self, by: By, value: str) -> bool:
        """
        Check if an element is visible on the page.
        
        Args:
            by: The locator strategy (e.g., By.CSS_SELECTOR)
            value: The locator value
            
        Returns:
            bool: True if element is visible, False otherwise
        """
        try:
            element = self.find_element_visible(by, value)
            return element is not None and element.is_displayed()
        except Exception:
            return False

    def get_page_title_element(self) -> WebElement:
        """
        Get the page title element.
        
        Returns:
            WebElement: The page title element
        """
        return self.find_element_visible(*self.PAGE_TITLE)

    def get_inventory_container_element(self) -> WebElement:
        """
        Get the inventory container element.
        
        Returns:
            WebElement: The inventory container element
        """
        return self.find_element_visible(*self.INVENTORY_CONTAINER)

    def get_sort_dropdown_element(self) -> WebElement:
        """
        Get the sort dropdown element.
        
        Returns:
            WebElement: The sort dropdown element
        """
        return self.find_element_clickable(*self.SORT_DROPDOWN)

    def get_shopping_cart_element(self) -> WebElement:
        """
        Get the shopping cart link element.
        
        Returns:
            WebElement: The shopping cart link element
        """
        return self.find_element_clickable(*self.SHOPPING_CART_LINK)

    def get_burger_menu_element(self) -> WebElement:
        """
        Get the burger menu button element.
        
        Returns:
            WebElement: The burger menu button element
        """
        return self.find_element_clickable(*self.BURGER_MENU_BUTTON)

    def get_page_title(self) -> str:
        """
        Get the page title text.
        
        Returns:
            str: The page title text
        """
        return self.get_element_text(*self.PAGE_TITLE)

    def is_products_page_displayed(self) -> bool:
        """
        Check if the products page is displayed.
        
        Returns:
            bool: True if products page is displayed, False otherwise
        """
        return self.is_element_present(*self.INVENTORY_CONTAINER) and \
               self.is_element_present(*self.PAGE_TITLE)

    def is_page_loaded(self) -> bool:
        """
        Check if the page is fully loaded.
        
        Returns:
            bool: True if page is loaded, False otherwise
        """
        return self.is_products_page_displayed()

    def is_on_page(self) -> bool:
        """
        Verify user is on the products page.
        
        Returns:
            bool: True if on products page, False otherwise
        """
        return self.is_products_page_displayed() and "Products" in self.get_page_title()

    def get_product_count(self) -> int:
        """
        Get the total count of products displayed.
        
        Returns:
            int: Number of products on the page
        """
        products = self.driver.find_elements(*self.INVENTORY_ITEM)
        return len(products)

    def get_all_product_items(self) -> List[WebElement]:
        """
        Get all product item elements displayed on the page.
        
        Returns:
            List[WebElement]: List of product item WebElements
        """
        return self.driver.find_elements(*self.INVENTORY_ITEM)

    def get_all_product_names(self) -> List[str]:
        """
        Get all product names displayed on the page.
        
        Returns:
            List[str]: List of product names
        """
        name_elements = self.driver.find_elements(*self.INVENTORY_ITEM_NAME)
        return [element.text for element in name_elements]

    def get_all_product_prices(self) -> List[str]:
        """
        Get all product prices displayed on the page.
        
        Returns:
            List[str]: List of product prices as strings (e.g., "$29.99")
        """
        price_elements = self.driver.find_elements(*self.INVENTORY_ITEM_PRICE)
        return [element.text for element in price_elements]

    def _get_price_as_float(self, price_str: str) -> float:
        """
        Convert price string to float.
        
        Args:
            price_str: Price string (e.g., "$29.99")
            
        Returns:
            float: Price as float value
        """
        return float(price_str.replace("$", ""))

    def get_all_product_prices_as_floats(self) -> List[float]:
        """
        Get all product prices as float values.
        
        Returns:
            List[float]: List of product prices as floats
        """
        prices = self.get_all_product_prices()
        return [self._get_price_as_float(price) for price in prices]

    def select_sort_option(self, option_value: str) -> None:
        """
        Select a sort option from the dropdown.
        
        Args:
            option_value: The value of the sort option to select
                         Options: 'az', 'za', 'lohi', 'hilo'
        """
        from selenium.webdriver.support.ui import Select
        dropdown = self.get_sort_dropdown_element()
        select = Select(dropdown)
        select.select_by_value(option_value)

    def get_active_sort_option(self) -> str:
        """
        Get the currently active sort option.
        
        Returns:
            str: The value of the currently selected sort option
        """
        from selenium.webdriver.support.ui import Select
        dropdown = self.get_sort_dropdown_element()
        select = Select(dropdown)
        return select.first_selected_option.get_attribute("value")

    def _format_product_id(self, product_name: str) -> str:
        """
        Format product name to match data-test attribute format.
        
        Args:
            product_name: The product name to format
            
        Returns:
            str: Formatted product ID for use in selectors
        """
        return product_name.lower().replace(" ", "-")

    def add_product_to_cart(self, product_name: str) -> None:
        """
        Add a product to the cart by its name.
        
        Args:
            product_name: The name of the product to add
        """
        product_id = self._format_product_id(product_name)
        selector = self.ADD_TO_CART_BUTTON_TEMPLATE.format(product_id=product_id)
        self.click(By.CSS_SELECTOR, selector)

    def remove_product_from_cart(self, product_name: str) -> None:
        """
        Remove a product from the cart by its name.
        
        Args:
            product_name: The name of the product to remove
        """
        product_id = self._format_product_id(product_name)
        selector = self.REMOVE_BUTTON_TEMPLATE.format(product_id=product_id)
        self.click(By.CSS_SELECTOR, selector)

    def get_cart_badge_count(self) -> int:
        """
        Get the count displayed on the cart badge.
        
        Returns:
            int: Number of items in cart, 0 if badge not present
        """
        if self.is_element_present(*self.SHOPPING_CART_BADGE):
            badge_text = self.get_element_text(*self.SHOPPING_CART_BADGE)
            return int(badge_text) if badge_text else 0
        return 0

    def click_shopping_cart(self) -> None:
        """
        Click the shopping cart link to navigate to cart page.
        """
        self.click(*self.SHOPPING_CART_LINK)

    def open_burger_menu(self) -> None:
        """
        Open the burger menu.
        """
        self.click(*self.BURGER_MENU_BUTTON)

    def is_inventory_container_visible(self) -> bool:
        """
        Check if the inventory container is visible.
        
        Returns:
            bool: True if inventory container is visible, False otherwise
        """
        return self.is_element_present(*self.INVENTORY_CONTAINER)

    def get_products_sorted_by_name(self, ascending: bool = True) -> List[str]:
        """
        Get product names sorted alphabetically.
        
        Args:
            ascending: If True, sort A-Z; if False, sort Z-A
            
        Returns:
            List[str]: Sorted list of product names
        """
        names = self.get_all_product_names()
        return sorted(names, reverse=not ascending)

    def verify_products_sorted_az(self) -> bool:
        """
        Verify products are sorted alphabetically A-Z.
        
        Returns:
            bool: True if products are sorted A-Z, False otherwise
        """
        current_names = self.get_all_product_names()
        expected_names = sorted(current_names)
        return current_names == expected_names

    def verify_products_sorted_za(self) -> bool:
        """
        Verify products are sorted alphabetically Z-A.
        
        Returns:
            bool: True if products are sorted Z-A, False otherwise
        """
        current_names = self.get_all_product_names()
        expected_names = sorted(current_names, reverse=True)
        return current_names == expected_names

    def verify_products_sorted_price_low_high(self) -> bool:
        """
        Verify products are sorted by price low to high.
        
        Returns:
            bool: True if products are sorted by price ascending, False otherwise
        """
        current_prices = self.get_all_product_prices_as_floats()
        expected_prices = sorted(current_prices)
        return current_prices == expected_prices

    def verify_products_sorted_price_high_low(self) -> bool:
        """
        Verify products are sorted by price high to low.
        
        Returns:
            bool: True if products are sorted by price descending, False otherwise
        """
        current_prices = self.get_all_product_prices_as_floats()
        expected_prices = sorted(current_prices, reverse=True)
        return current_prices == expected_prices

    def is_title_displayed(self) -> bool:
        """
        Check if the page title is displayed.
        
        Returns:
            bool: True if title is displayed, False otherwise
        """
        return self.is_element_present(*self.PAGE_TITLE)

    def get_title_text(self) -> str:
        """
        Get the title text.
        
        Returns:
            str: The title text
        """
        return self.get_page_title()