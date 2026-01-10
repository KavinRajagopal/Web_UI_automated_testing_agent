"""
Cart Page Object Model for Sauce Demo application.
Uses Selenium WebDriver for browser automation.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from typing import List, Dict, Optional
from pages.base_page import BasePage


class CartPage(BasePage):
    """Page Object for the Shopping Cart page."""
    
    # Page URL
    PAGE_URL = "https://www.saucedemo.com/cart.html"
    
    # Locators
    PAGE_TITLE = (By.CSS_SELECTOR, "[data-test='title']")
    CART_LIST = (By.CSS_SELECTOR, "[data-test='cart-list']")
    CART_ITEM = (By.CSS_SELECTOR, "[data-test='inventory-item']")
    CART_BADGE = (By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")
    CONTINUE_SHOPPING_BUTTON = (By.CSS_SELECTOR, "[data-test='continue-shopping']")
    CHECKOUT_BUTTON = (By.CSS_SELECTOR, "[data-test='checkout']")
    
    # Item-specific locators (used with formatting)
    ITEM_NAME = (By.CSS_SELECTOR, "[data-test='inventory-item-name']")
    ITEM_DESCRIPTION = (By.CSS_SELECTOR, "[data-test='inventory-item-desc']")
    ITEM_PRICE = (By.CSS_SELECTOR, "[data-test='inventory-item-price']")
    ITEM_QUANTITY = (By.CSS_SELECTOR, "[data-test='item-quantity']")
    REMOVE_BUTTON = (By.CSS_SELECTOR, "button[data-test^='remove-']")
    
    def __init__(self, driver):
        """
        Initialize CartPage with WebDriver instance.
        
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
    
    def get_cart_list_element(self) -> Optional[WebElement]:
        """
        Get the cart list container element.
        
        Returns:
            WebElement: The cart list element or None if not found
        """
        if self.is_element_present(*self.CART_LIST):
            return self.find_element(*self.CART_LIST)
        return None
    
    def get_cart_item_elements(self) -> List[WebElement]:
        """
        Get all cart item elements.
        
        Returns:
            List[WebElement]: List of cart item elements
        """
        if self.is_element_present(*self.CART_ITEM):
            return self.driver.find_elements(*self.CART_ITEM)
        return []
    
    def get_cart_badge_element(self) -> Optional[WebElement]:
        """
        Get the cart badge element showing item count.
        
        Returns:
            WebElement: The cart badge element or None if not present
        """
        if self.is_element_present(*self.CART_BADGE):
            return self.find_element(*self.CART_BADGE)
        return None
    
    def get_continue_shopping_button_element(self) -> WebElement:
        """
        Get the Continue Shopping button element.
        
        Returns:
            WebElement: The Continue Shopping button
        """
        return self.find_element_clickable(*self.CONTINUE_SHOPPING_BUTTON)
    
    def get_checkout_button_element(self) -> WebElement:
        """
        Get the Checkout button element.
        
        Returns:
            WebElement: The Checkout button
        """
        return self.find_element_clickable(*self.CHECKOUT_BUTTON)
    
    # Page Methods
    def get_page_title(self) -> str:
        """
        Get the page title text.
        
        Returns:
            str: The page title text
        """
        return self.get_element_text(*self.PAGE_TITLE)
    
    def is_cart_page_displayed(self) -> bool:
        """
        Check if the cart page is displayed.
        
        Returns:
            bool: True if cart page is displayed, False otherwise
        """
        return (self.is_element_present(*self.PAGE_TITLE) and 
                "Your Cart" in self.get_page_title())
    
    def is_page_loaded(self) -> bool:
        """
        Check if the cart page is fully loaded.
        
        Returns:
            bool: True if page is loaded, False otherwise
        """
        return self.is_cart_page_displayed()
    
    def is_on_page(self) -> bool:
        """
        Verify if currently on the cart page.
        
        Returns:
            bool: True if on cart page, False otherwise
        """
        return "cart.html" in self.driver.current_url
    
    def get_cart_item_count(self) -> int:
        """
        Get the number of items in the cart from the badge.
        
        Returns:
            int: Number of items in cart, 0 if cart is empty
        """
        badge = self.get_cart_badge_element()
        if badge:
            try:
                return int(badge.text)
            except ValueError:
                return 0
        return 0
    
    def get_cart_items(self) -> List[Dict[str, str]]:
        """
        Get all items in the cart with their details.
        
        Returns:
            List[Dict]: List of dictionaries containing item details
                       (name, description, price, quantity)
        """
        items = []
        cart_item_elements = self.get_cart_item_elements()
        
        for item_element in cart_item_elements:
            item_data = {}
            
            # Get item name
            name_elements = item_element.find_elements(*self.ITEM_NAME)
            if name_elements:
                item_data['name'] = name_elements[0].text
            
            # Get item description
            desc_elements = item_element.find_elements(*self.ITEM_DESCRIPTION)
            if desc_elements:
                item_data['description'] = desc_elements[0].text
            
            # Get item price
            price_elements = item_element.find_elements(*self.ITEM_PRICE)
            if price_elements:
                item_data['price'] = price_elements[0].text
            
            # Get item quantity
            qty_elements = item_element.find_elements(*self.ITEM_QUANTITY)
            if qty_elements:
                item_data['quantity'] = qty_elements[0].text
            
            items.append(item_data)
        
        return items
    
    def get_item_quantity(self, item_name: str) -> int:
        """
        Get the quantity of a specific item in the cart.
        
        Args:
            item_name: Name of the item to check
            
        Returns:
            int: Quantity of the item, 0 if not found
        """
        cart_item_elements = self.get_cart_item_elements()
        
        for item_element in cart_item_elements:
            name_elements = item_element.find_elements(*self.ITEM_NAME)
            if name_elements and name_elements[0].text == item_name:
                qty_elements = item_element.find_elements(*self.ITEM_QUANTITY)
                if qty_elements:
                    try:
                        return int(qty_elements[0].text)
                    except ValueError:
                        return 0
        return 0
    
    def remove_item_from_cart(self, item_name: str) -> bool:
        """
        Remove a specific item from the cart.
        
        Args:
            item_name: Name of the item to remove
            
        Returns:
            bool: True if item was removed, False if not found
        """
        cart_item_elements = self.get_cart_item_elements()
        
        for item_element in cart_item_elements:
            name_elements = item_element.find_elements(*self.ITEM_NAME)
            if name_elements and name_elements[0].text == item_name:
                remove_buttons = item_element.find_elements(*self.REMOVE_BUTTON)
                if remove_buttons:
                    remove_buttons[0].click()
                    return True
        return False
    
    def click_continue_shopping(self) -> None:
        """
        Click the Continue Shopping button to return to inventory.
        """
        self.click(*self.CONTINUE_SHOPPING_BUTTON)
    
    def click_checkout(self) -> None:
        """
        Click the Checkout button to proceed to checkout.
        """
        self.click(*self.CHECKOUT_BUTTON)
    
    def is_cart_empty(self) -> bool:
        """
        Check if the cart is empty.
        
        Returns:
            bool: True if cart is empty, False otherwise
        """
        return len(self.get_cart_item_elements()) == 0
    
    def is_title_displayed(self) -> bool:
        """
        Check if the page title is displayed.
        
        Returns:
            bool: True if title is displayed, False otherwise
        """
        return self.is_element_present(*self.PAGE_TITLE)
    
    def get_title_text(self) -> str:
        """
        Get the title text of the page.
        
        Returns:
            str: The title text
        """
        return self.get_page_title()
    
    def is_checkout_button_visible(self) -> bool:
        """
        Check if the checkout button is visible.
        
        Returns:
            bool: True if checkout button is visible, False otherwise
        """
        return self.is_element_present(*self.CHECKOUT_BUTTON)
    
    def is_continue_shopping_button_visible(self) -> bool:
        """
        Check if the continue shopping button is visible.
        
        Returns:
            bool: True if continue shopping button is visible, False otherwise
        """
        return self.is_element_present(*self.CONTINUE_SHOPPING_BUTTON)
    
    def get_total_items_in_cart(self) -> int:
        """
        Get the total number of items displayed in the cart list.
        
        Returns:
            int: Number of item rows in the cart
        """
        return len(self.get_cart_item_elements())
    
    def get_item_names(self) -> List[str]:
        """
        Get a list of all item names in the cart.
        
        Returns:
            List[str]: List of item names
        """
        names = []
        cart_item_elements = self.get_cart_item_elements()
        
        for item_element in cart_item_elements:
            name_elements = item_element.find_elements(*self.ITEM_NAME)
            if name_elements:
                names.append(name_elements[0].text)
        
        return names
    
    def is_item_in_cart(self, item_name: str) -> bool:
        """
        Check if a specific item is in the cart.
        
        Args:
            item_name: Name of the item to check
            
        Returns:
            bool: True if item is in cart, False otherwise
        """
        return item_name in self.get_item_names()