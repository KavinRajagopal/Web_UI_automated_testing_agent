"""
Cart Page Object Model for Sauce Demo application.
Uses Selenium WebDriver for browser automation.
"""

from typing import List, Dict
from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class CartPage(BasePage):
    """
    Page Object Model for the Cart page.
    Handles cart viewing, item management, and checkout navigation.
    """


    # Element Locators (auto-generated from metadata)
    HEADER_CONTAINER = (By.ID, "header_container")
    PRIMARY_HEADER = (By.CSS_SELECTOR, "[data-test='primary-header']")
    REACT_BURGER_MENU_BTN = (By.ID, "react-burger-menu-btn")
    OPEN_MENU = (By.CSS_SELECTOR, "[data-test='open-menu']")
    SHOPPING_CART_LINK = (By.CSS_SELECTOR, "[data-test='shopping-cart-link']")
    SECONDARY_HEADER = (By.CSS_SELECTOR, "[data-test='secondary-header']")
    TITLE = (By.CSS_SELECTOR, "[data-test='title']")
    ACTIVE_OPTION = (By.CSS_SELECTOR, "[data-test='active-option']")
    PRODUCT_SORT_CONTAINER = (By.CSS_SELECTOR, "[data-test='product-sort-container']")
    INVENTORY_CONTAINER = (By.ID, "inventory_container")
    INVENTORY_LIST = (By.CSS_SELECTOR, "[data-test='inventory-list']")
    INVENTORY_ITEM = (By.CSS_SELECTOR, "[data-test='inventory-item']")
    ITEM_4_IMG_LINK = (By.ID, "item_4_img_link")
    INVENTORY_ITEM_SAUCE_LABS_BACKPACK_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-backpack-img']")
    INVENTORY_ITEM_DESCRIPTION = (By.CSS_SELECTOR, "[data-test='inventory-item-description']")
    ITEM_4_TITLE_LINK = (By.ID, "item_4_title_link")
    INVENTORY_ITEM_NAME = (By.CSS_SELECTOR, "[data-test='inventory-item-name']")
    INVENTORY_ITEM_DESC = (By.CSS_SELECTOR, "[data-test='inventory-item-desc']")
    INVENTORY_ITEM_PRICE = (By.CSS_SELECTOR, "[data-test='inventory-item-price']")
    ADD_TO_CART_SAUCE_LABS_BACKPACK = (By.ID, "add-to-cart-sauce-labs-backpack")
    ITEM_0_IMG_LINK = (By.ID, "item_0_img_link")
    INVENTORY_ITEM_SAUCE_LABS_BIKE_LIGHT_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-bike-light-img']")
    ITEM_0_TITLE_LINK = (By.ID, "item_0_title_link")
    ADD_TO_CART_SAUCE_LABS_BIKE_LIGHT = (By.ID, "add-to-cart-sauce-labs-bike-light")
    ITEM_1_IMG_LINK = (By.ID, "item_1_img_link")
    INVENTORY_ITEM_SAUCE_LABS_BOLT_T_SHIRT_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-bolt-t-shirt-img']")
    ITEM_1_TITLE_LINK = (By.ID, "item_1_title_link")
    ADD_TO_CART_SAUCE_LABS_BOLT_T_SHIRT = (By.ID, "add-to-cart-sauce-labs-bolt-t-shirt")
    ITEM_5_IMG_LINK = (By.ID, "item_5_img_link")
    INVENTORY_ITEM_SAUCE_LABS_FLEECE_JACKET_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-fleece-jacket-img']")
    ITEM_5_TITLE_LINK = (By.ID, "item_5_title_link")
    ADD_TO_CART_SAUCE_LABS_FLEECE_JACKET = (By.ID, "add-to-cart-sauce-labs-fleece-jacket")
    ITEM_2_IMG_LINK = (By.ID, "item_2_img_link")
    INVENTORY_ITEM_SAUCE_LABS_ONESIE_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-onesie-img']")
    ITEM_2_TITLE_LINK = (By.ID, "item_2_title_link")
    ADD_TO_CART_SAUCE_LABS_ONESIE = (By.ID, "add-to-cart-sauce-labs-onesie")
    ITEM_3_IMG_LINK = (By.ID, "item_3_img_link")
    INVENTORY_ITEM_TEST_ALLTHETHINGS__T_SHIRT__RED__IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-test.allthethings()-t-shirt-(red)-img']")
    ITEM_3_TITLE_LINK = (By.ID, "item_3_title_link")
    ADD_TO_CART_TEST_ALLTHETHINGS__T_SHIRT__RED = (By.ID, "add-to-cart-test.allthethings()-t-shirt-(red)")
    FOOTER = (By.CSS_SELECTOR, "[data-test='footer']")
    SOCIAL_TWITTER = (By.CSS_SELECTOR, "[data-test='social-twitter']")
    SOCIAL_FACEBOOK = (By.CSS_SELECTOR, "[data-test='social-facebook']")
    SOCIAL_LINKEDIN = (By.CSS_SELECTOR, "[data-test='social-linkedin']")
    FOOTER_COPY = (By.CSS_SELECTOR, "[data-test='footer-copy']")
    def is_page_loaded(self) -> bool:
        """
        Check if the cart page is fully loaded.
        
        Returns:
            bool: True if the required page elements are present, False otherwise.
        """
        return self.is_element_present(*self.HEADER_CONTAINER, timeout=10)

    def is_on_page(self) -> bool:
        """
        Alias for is_page_loaded().
        
        Returns:
            bool: True if on the cart page, False otherwise.
        """
        return self.is_page_loaded()

    def is_cart_page_displayed(self) -> bool:
        """
        Check if the cart page is displayed.
        
        Returns:
            bool: True if the cart page is displayed, False otherwise.
        """
        return self.is_page_loaded() and self.is_element_present(*self.TITLE, timeout=5)

    def get_page_title(self) -> str:
        """
        Get the title of the cart page.
        
        Returns:
            str: The page title text.
        """
        return self.get_element_text(*self.TITLE)

    def get_cart_items(self) -> List[Dict[str, str]]:
        """
        Get all items currently in the cart.
        
        Returns:
            List[Dict[str, str]]: List of dictionaries containing item details
                                  (name, description, price).
        """
        items = []
        try:
            # Find all cart item containers
            cart_items = self.driver.find_elements(*self.INVENTORY_ITEM)
            
            for item in cart_items:
                item_data = {}
                
                # Get item name
                try:
                    name_element = item.find_element(By.CLASS_NAME, "inventory_item_name")
                    item_data["name"] = name_element.text
                except Exception:
                    item_data["name"] = ""
                
                # Get item description
                try:
                    desc_element = item.find_element(By.CLASS_NAME, "inventory_item_desc")
                    item_data["description"] = desc_element.text
                except Exception:
                    item_data["description"] = ""
                
                # Get item price
                try:
                    price_element = item.find_element(By.CLASS_NAME, "inventory_item_price")
                    item_data["price"] = price_element.text
                except Exception:
                    item_data["price"] = ""
                
                items.append(item_data)
                
        except Exception:
            pass
        
        return items

    def get_cart_item_count(self) -> int:
        """
        Get the number of items in the cart.
        
        Returns:
            int: The count of items in the cart.
        """
        try:
            cart_items = self.driver.find_elements(*self.INVENTORY_ITEM)
            return len(cart_items)
        except Exception:
            return 0

    def remove_item_from_cart(self, item_name: str) -> bool:
        """
        Remove a specific item from the cart by its name.
        
        Args:
            item_name: The name of the item to remove.
            
        Returns:
            bool: True if item was removed successfully, False otherwise.
        """
        try:
            # Find all cart items
            cart_items = self.driver.find_elements(*self.INVENTORY_ITEM)
            
            for item in cart_items:
                try:
                    name_element = item.find_element(By.CLASS_NAME, "inventory_item_name")
                    if name_element.text == item_name:
                        # Find and click the remove button within this item
                        remove_button = item.find_element(By.CSS_SELECTOR, "button[id^='remove-']")
                        remove_button.click()
                        return True
                except Exception:
                    continue
            
            return False
        except Exception:
            return False

    def click_checkout(self) -> None:
        """
        Click the checkout button to proceed to checkout.
        """
        checkout_locator = (By.ID, "checkout")
        self.click(*checkout_locator)

    def click_continue_shopping(self) -> None:
        """
        Click the continue shopping button to return to the inventory page.
        """
        continue_shopping_locator = (By.ID, "continue-shopping")
        self.click(*continue_shopping_locator)

    def get_cart_badge_count(self) -> int:
        """
        Get the count displayed on the shopping cart badge.
        
        Returns:
            int: The number shown on the cart badge, 0 if not present.
        """
        try:
            badge_locator = (By.CLASS_NAME, "shopping_cart_badge")
            if self.is_element_present(*badge_locator, timeout=2):
                badge_text = self.get_element_text(*badge_locator)
                return int(badge_text)
        except Exception:
            pass
        return 0

    def click_shopping_cart(self) -> None:
        """
        Click the shopping cart link in the header.
        """
        self.click(*self.SHOPPING_CART_LINK)

    def click_item_link(self, item_name: str) -> bool:
        """
        Click on an item's name link to view its details.
        
        Args:
            item_name: The name of the item to click.
            
        Returns:
            bool: True if item link was clicked, False otherwise.
        """
        try:
            cart_items = self.driver.find_elements(*self.INVENTORY_ITEM)
            
            for item in cart_items:
                try:
                    name_element = item.find_element(By.CLASS_NAME, "inventory_item_name")
                    if name_element.text == item_name:
                        name_element.click()
                        return True
                except Exception:
                    continue
            
            return False
        except Exception:
            return False

    def is_item_in_cart(self, item_name: str) -> bool:
        """
        Check if a specific item is in the cart.
        
        Args:
            item_name: The name of the item to check.
            
        Returns:
            bool: True if item is in cart, False otherwise.
        """
        cart_items = self.get_cart_items()
        for item in cart_items:
            if item.get("name") == item_name:
                return True
        return False

    def get_item_price(self, item_name: str) -> str:
        """
        Get the price of a specific item in the cart.
        
        Args:
            item_name: The name of the item.
            
        Returns:
            str: The price of the item, empty string if not found.
        """
        cart_items = self.get_cart_items()
        for item in cart_items:
            if item.get("name") == item_name:
                return item.get("price", "")
        return ""

    def remove_all_items(self) -> None:
        """
        Remove all items from the cart.
        """
        while self.get_cart_item_count() > 0:
            try:
                remove_button = self.driver.find_element(By.CSS_SELECTOR, "button[id^='remove-']")
                remove_button.click()
            except Exception:
                break