"""
Cart Page Object Model for Sauce Demo application.
Uses Selenium WebDriver for browser automation.
"""

from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from pages.base_page import BasePage


class CartPage(BasePage):
    """Page Object for the Shopping Cart page."""

    # Locators
    PAGE_TITLE = (By.CSS_SELECTOR, "[data-test='title']")
    CART_LIST = (By.CSS_SELECTOR, "[data-test='cart-list']")
    CART_ITEM = (By.CSS_SELECTOR, "[data-test='inventory-item']")
    CART_ITEM_NAME = (By.CSS_SELECTOR, "[data-test='inventory-item-name']")
    CART_ITEM_PRICE = (By.CSS_SELECTOR, "[data-test='inventory-item-price']")
    CART_ITEM_DESC = (By.CSS_SELECTOR, "[data-test='inventory-item-desc']")
    REMOVE_BUTTON = (By.CSS_SELECTOR, "button[data-test^='remove-']")
    CONTINUE_SHOPPING_BUTTON = (By.CSS_SELECTOR, "[data-test='continue-shopping']")
    CHECKOUT_BUTTON = (By.CSS_SELECTOR, "[data-test='checkout']")
    CART_BADGE = (By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")
    CART_CONTENTS = (By.CSS_SELECTOR, "[data-test='cart-contents-container']")

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

    def get_cart_list_element(self) -> WebElement:
        """
        Get the cart list container element.

        Returns:
            WebElement: The cart list element
        """
        return self.find_element_visible(*self.CART_LIST)

    def get_cart_item_elements(self) -> List[WebElement]:
        """
        Get all cart item elements.

        Returns:
            List[WebElement]: List of cart item elements
        """
        if self.is_element_present(*self.CART_ITEM, timeout=3):
            return self.driver.find_elements(*self.CART_ITEM)
        return []

    def get_continue_shopping_button(self) -> WebElement:
        """
        Get the continue shopping button element.

        Returns:
            WebElement: The continue shopping button
        """
        return self.find_element_clickable(*self.CONTINUE_SHOPPING_BUTTON)

    def get_checkout_button(self) -> WebElement:
        """
        Get the checkout button element.

        Returns:
            WebElement: The checkout button
        """
        return self.find_element_clickable(*self.CHECKOUT_BUTTON)

    # Page Verification Methods
    def is_on_cart_page(self) -> bool:
        """
        Check if currently on the cart page.

        Returns:
            bool: True if on cart page, False otherwise
        """
        try:
            title_element = self.find_element_visible(*self.PAGE_TITLE)
            return title_element.text == "Your Cart" and "/cart.html" in self.driver.current_url
        except Exception:
            return False

    def is_page_loaded(self) -> bool:
        """
        Check if the cart page is fully loaded.

        Returns:
            bool: True if page is loaded, False otherwise
        """
        return self.is_element_present(*self.CART_CONTENTS) and self.is_element_present(*self.PAGE_TITLE)

    def is_title_displayed(self) -> bool:
        """
        Check if the page title is displayed.

        Returns:
            bool: True if title is displayed, False otherwise
        """
        return self.is_element_present(*self.PAGE_TITLE)

    # Title Methods
    def get_page_title(self) -> str:
        """
        Get the page title text.

        Returns:
            str: The page title text
        """
        return self.get_element_text(*self.PAGE_TITLE)

    def get_title_text(self) -> str:
        """
        Get the page title text (alias for get_page_title).

        Returns:
            str: The page title text
        """
        return self.get_page_title()

    # Cart Item Methods
    def get_cart_items(self) -> List[WebElement]:
        """
        Get all items currently in the cart.

        Returns:
            List[WebElement]: List of cart item elements
        """
        return self.get_cart_item_elements()

    def get_cart_item_count(self) -> int:
        """
        Get the number of items in the cart.

        Returns:
            int: Number of items in cart
        """
        return len(self.get_cart_item_elements())

    def get_item_names(self) -> List[str]:
        """
        Get names of all items in the cart.

        Returns:
            List[str]: List of item names
        """
        if self.is_element_present(*self.CART_ITEM_NAME, timeout=3):
            name_elements = self.driver.find_elements(*self.CART_ITEM_NAME)
            return [element.text for element in name_elements]
        return []

    def get_item_prices(self) -> List[str]:
        """
        Get prices of all items in the cart.

        Returns:
            List[str]: List of item prices (e.g., ['$29.99', '$15.99'])
        """
        if self.is_element_present(*self.CART_ITEM_PRICE, timeout=3):
            price_elements = self.driver.find_elements(*self.CART_ITEM_PRICE)
            return [element.text for element in price_elements]
        return []

    def get_item_prices_as_float(self) -> List[float]:
        """
        Get prices of all items in the cart as float values.

        Returns:
            List[float]: List of item prices as floats
        """
        prices = self.get_item_prices()
        return [float(price.replace('$', '')) for price in prices]

    def get_cart_total(self) -> float:
        """
        Calculate the total price of all items in cart.

        Returns:
            float: Total price of all items
        """
        return sum(self.get_item_prices_as_float())

    # Remove Item Methods
    def remove_item(self, item_name: str) -> None:
        """
        Remove a specific item from the cart by name.

        Args:
            item_name: Name of the item to remove
        """
        # Convert item name to data-test format (lowercase, replace spaces with hyphens)
        item_id = item_name.lower().replace(' ', '-')
        remove_locator = (By.CSS_SELECTOR, f"[data-test='remove-{item_id}']")
        self.click(*remove_locator)

    def remove_item_by_index(self, index: int) -> None:
        """
        Remove an item from the cart by its index.

        Args:
            index: Index of the item to remove (0-based)
        """
        remove_buttons = self.driver.find_elements(*self.REMOVE_BUTTON)
        if 0 <= index < len(remove_buttons):
            remove_buttons[index].click()
        else:
            raise IndexError(f"No item at index {index}. Cart has {len(remove_buttons)} items.")

    def remove_all_items(self) -> None:
        """
        Remove all items from the cart.
        """
        while not self.is_cart_empty():
            remove_buttons = self.driver.find_elements(*self.REMOVE_BUTTON)
            if remove_buttons:
                remove_buttons[0].click()
            else:
                break

    # Navigation Methods
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

    # Cart State Methods
    def is_cart_empty(self) -> bool:
        """
        Check if the cart is empty.

        Returns:
            bool: True if cart is empty, False otherwise
        """
        return self.get_cart_item_count() == 0

    def is_item_in_cart(self, item_name: str) -> bool:
        """
        Check if a specific item is in the cart.

        Args:
            item_name: Name of the item to check

        Returns:
            bool: True if item is in cart, False otherwise
        """
        return item_name in self.get_item_names()

    def get_cart_badge_count(self) -> Optional[int]:
        """
        Get the count displayed on the cart badge.

        Returns:
            Optional[int]: Badge count or None if badge not present
        """
        if self.is_element_present(*self.CART_BADGE, timeout=2):
            badge_text = self.get_element_text(*self.CART_BADGE)
            return int(badge_text) if badge_text else None
        return None

    def is_checkout_button_enabled(self) -> bool:
        """
        Check if the checkout button is enabled.

        Returns:
            bool: True if checkout button is enabled
        """
        button = self.find_element(*self.CHECKOUT_BUTTON)
        return button.is_enabled()

    def is_continue_shopping_button_enabled(self) -> bool:
        """
        Check if the continue shopping button is enabled.

        Returns:
            bool: True if continue shopping button is enabled
        """
        button = self.find_element(*self.CONTINUE_SHOPPING_BUTTON)
        return button.is_enabled()