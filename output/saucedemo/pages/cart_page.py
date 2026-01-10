"""
Cart Page Object Model for Sauce Demo application.
"""

from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from pages.base_page import BasePage


class CartPage(BasePage):
    """Page object for the Shopping Cart page."""

    # Page URL
    PAGE_URL = "/cart.html"

    # Locators
    PAGE_TITLE = (By.CSS_SELECTOR, "[data-test='title']")
    CART_LIST = (By.CSS_SELECTOR, "[data-test='cart-list']")
    CART_ITEM = (By.CSS_SELECTOR, "[data-test='inventory-item']")
    CART_ITEM_NAME = (By.CSS_SELECTOR, "[data-test='inventory-item-name']")
    CART_ITEM_DESC = (By.CSS_SELECTOR, "[data-test='inventory-item-desc']")
    CART_ITEM_PRICE = (By.CSS_SELECTOR, "[data-test='inventory-item-price']")
    CART_QUANTITY = (By.CSS_SELECTOR, "[data-test='item-quantity']")
    REMOVE_BUTTON = (By.CSS_SELECTOR, "button[data-test^='remove-']")
    CHECKOUT_BUTTON = (By.CSS_SELECTOR, "[data-test='checkout']")
    CONTINUE_SHOPPING_BUTTON = (By.CSS_SELECTOR, "[data-test='continue-shopping']")
    CART_BADGE = (By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")

    def __init__(self, driver):
        """
        Initialize the CartPage.

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
        try:
            self.find_element_visible(*self.CART_LIST)
            return self.driver.find_elements(*self.CART_ITEM)
        except Exception:
            return []

    def get_checkout_button_element(self) -> WebElement:
        """
        Get the checkout button element.

        Returns:
            WebElement: The checkout button element
        """
        return self.find_element_clickable(*self.CHECKOUT_BUTTON)

    def get_continue_shopping_button_element(self) -> WebElement:
        """
        Get the continue shopping button element.

        Returns:
            WebElement: The continue shopping button element
        """
        return self.find_element_clickable(*self.CONTINUE_SHOPPING_BUTTON)

    def get_cart_badge_element(self) -> WebElement:
        """
        Get the cart badge element showing item count.

        Returns:
            WebElement: The cart badge element
        """
        return self.find_element_visible(*self.CART_BADGE)

    # Page State Methods
    def is_on_cart_page(self) -> bool:
        """
        Check if the user is currently on the cart page.

        Returns:
            bool: True if on cart page, False otherwise
        """
        try:
            current_url = self.driver.current_url
            title_element = self.find_element_visible(*self.PAGE_TITLE)
            return (
                self.PAGE_URL in current_url
                and title_element.text.lower() == "your cart"
            )
        except Exception:
            return False

    def is_page_loaded(self) -> bool:
        """
        Check if the cart page is fully loaded.

        Returns:
            bool: True if page is loaded, False otherwise
        """
        return self.is_on_cart_page()

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
        return self.get_element_text(*self.PAGE_TITLE)

    def get_page_title(self) -> str:
        """
        Get the page title text (alias for get_title_text).

        Returns:
            str: The page title text
        """
        return self.get_title_text()

    def is_on_page(self) -> bool:
        """
        Verify the user is on the cart page.

        Returns:
            bool: True if on cart page, False otherwise
        """
        return self.is_on_cart_page()

    # Cart Item Methods
    def get_cart_items(self) -> List[dict]:
        """
        Get all items in the cart with their details.

        Returns:
            List[dict]: List of dictionaries containing item details
                       (name, description, price, quantity)
        """
        items = []
        cart_item_elements = self.get_cart_item_elements()

        for item_element in cart_item_elements:
            try:
                name = item_element.find_element(*self.CART_ITEM_NAME).text
                description = item_element.find_element(*self.CART_ITEM_DESC).text
                price = item_element.find_element(*self.CART_ITEM_PRICE).text
                quantity = item_element.find_element(*self.CART_QUANTITY).text

                items.append({
                    "name": name,
                    "description": description,
                    "price": price,
                    "quantity": quantity,
                    "element": item_element
                })
            except Exception:
                continue

        return items

    def get_cart_item_count(self) -> int:
        """
        Get the number of items in the cart.

        Returns:
            int: Number of items in cart
        """
        return len(self.get_cart_item_elements())

    def get_cart_badge_count(self) -> int:
        """
        Get the count displayed on the cart badge.

        Returns:
            int: The count from cart badge, 0 if not present
        """
        try:
            badge_text = self.get_element_text(*self.CART_BADGE)
            return int(badge_text)
        except Exception:
            return 0

    def is_cart_empty(self) -> bool:
        """
        Check if the cart is empty.

        Returns:
            bool: True if cart is empty, False otherwise
        """
        return self.get_cart_item_count() == 0

    def remove_item(self, item_name: str) -> bool:
        """
        Remove an item from the cart by its name.

        Args:
            item_name: The name of the item to remove

        Returns:
            bool: True if item was removed, False otherwise
        """
        cart_items = self.get_cart_items()

        for item in cart_items:
            if item["name"] == item_name:
                try:
                    remove_button = item["element"].find_element(*self.REMOVE_BUTTON)
                    remove_button.click()
                    return True
                except Exception:
                    return False

        return False

    def remove_item_by_index(self, index: int) -> bool:
        """
        Remove an item from the cart by its index.

        Args:
            index: The index of the item to remove (0-based)

        Returns:
            bool: True if item was removed, False otherwise
        """
        cart_item_elements = self.get_cart_item_elements()

        if 0 <= index < len(cart_item_elements):
            try:
                remove_button = cart_item_elements[index].find_element(*self.REMOVE_BUTTON)
                remove_button.click()
                return True
            except Exception:
                return False

        return False

    def remove_all_items(self) -> None:
        """
        Remove all items from the cart.
        """
        while not self.is_cart_empty():
            self.remove_item_by_index(0)

    def get_item_by_name(self, item_name: str) -> dict:
        """
        Get item details by name.

        Args:
            item_name: The name of the item to find

        Returns:
            dict: Item details or empty dict if not found
        """
        cart_items = self.get_cart_items()

        for item in cart_items:
            if item["name"] == item_name:
                return item

        return {}

    def is_item_in_cart(self, item_name: str) -> bool:
        """
        Check if an item is in the cart.

        Args:
            item_name: The name of the item to check

        Returns:
            bool: True if item is in cart, False otherwise
        """
        return bool(self.get_item_by_name(item_name))

    # Navigation Methods
    def click_checkout(self) -> None:
        """
        Click the checkout button to proceed to checkout.
        """
        self.click(*self.CHECKOUT_BUTTON)

    def click_continue_shopping(self) -> None:
        """
        Click the continue shopping button to return to inventory.
        """
        self.click(*self.CONTINUE_SHOPPING_BUTTON)

    # Element State Methods
    def is_checkout_button_enabled(self) -> bool:
        """
        Check if the checkout button is enabled.

        Returns:
            bool: True if enabled, False otherwise
        """
        try:
            button = self.get_checkout_button_element()
            return button.is_enabled()
        except Exception:
            return False

    def is_continue_shopping_button_enabled(self) -> bool:
        """
        Check if the continue shopping button is enabled.

        Returns:
            bool: True if enabled, False otherwise
        """
        try:
            button = self.get_continue_shopping_button_element()
            return button.is_enabled()
        except Exception:
            return False