"""
Cart Page Object Model for Sauce Demo application.
Handles cart page interactions using Selenium WebDriver.
"""

from typing import List, Dict
from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class CartPage(BasePage):
    """Page object for the Cart page of Sauce Demo application."""


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
        Check if the cart page is loaded by verifying required elements are present.
        
        Returns:
            bool: True if the page is loaded, False otherwise.
        """
        return self.is_element_present(*self.HEADER_CONTAINER, timeout=10)

    def is_on_page(self) -> bool:
        """
        Alias for is_page_loaded() to check if on the cart page.
        
        Returns:
            bool: True if on the cart page, False otherwise.
        """
        return self.is_page_loaded()

    def is_cart_page_displayed(self) -> bool:
        """
        Check if the cart page is displayed.
        
        Returns:
            bool: True if cart page is displayed, False otherwise.
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
            # Find all inventory items in the cart
            item_elements = self.driver.find_elements(*self.INVENTORY_ITEM)
            
            for item in item_elements:
                item_data = {}
                try:
                    # Get item name
                    name_element = item.find_element(By.CLASS_NAME, "inventory_item_name")
                    item_data["name"] = name_element.text
                except:
                    item_data["name"] = ""
                
                try:
                    # Get item description
                    desc_element = item.find_element(By.CLASS_NAME, "inventory_item_desc")
                    item_data["description"] = desc_element.text
                except:
                    item_data["description"] = ""
                
                try:
                    # Get item price
                    price_element = item.find_element(By.CLASS_NAME, "inventory_item_price")
                    item_data["price"] = price_element.text
                except:
                    item_data["price"] = ""
                
                items.append(item_data)
        except:
            pass
        
        return items

    def get_cart_item_count(self) -> int:
        """
        Get the number of items in the cart.
        
        Returns:
            int: Number of items in the cart.
        """
        try:
            item_elements = self.driver.find_elements(*self.INVENTORY_ITEM)
            return len(item_elements)
        except:
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
            # Find all inventory items
            item_elements = self.driver.find_elements(*self.INVENTORY_ITEM)
            
            for item in item_elements:
                try:
                    name_element = item.find_element(By.CLASS_NAME, "inventory_item_name")
                    if name_element.text.lower() == item_name.lower():
                        # Find and click the remove button within this item
                        remove_button = item.find_element(By.CSS_SELECTOR, "button[id^='remove-']")
                        remove_button.click()
                        return True
                except:
                    continue
            return False
        except:
            return False

    def click_checkout(self) -> None:
        """
        Click the checkout button to proceed to checkout.
        """
        checkout_locator = (By.ID, "checkout")
        self.click(*checkout_locator)

    def click_continue_shopping(self) -> None:
        """
        Click the continue shopping button to return to inventory.
        """
        continue_shopping_locator = (By.ID, "continue-shopping")
        self.click(*continue_shopping_locator)

    def is_item_in_cart(self, item_name: str) -> bool:
        """
        Check if a specific item is in the cart.
        
        Args:
            item_name: The name of the item to check for.
            
        Returns:
            bool: True if item is in cart, False otherwise.
        """
        cart_items = self.get_cart_items()
        for item in cart_items:
            if item.get("name", "").lower() == item_name.lower():
                return True
        return False

    def click_shopping_cart(self) -> None:
        """
        Click the shopping cart link in the header.
        """
        self.click(*self.SHOPPING_CART_LINK)

    def open_menu(self) -> None:
        """
        Open the burger menu.
        """
        self.click(*self.REACT_BURGER_MENU_BTN)

    def click_twitter_link(self) -> None:
        """
        Click the Twitter social media link in the footer.
        """
        self.click(*self.SOCIAL_TWITTER)

    def click_facebook_link(self) -> None:
        """
        Click the Facebook social media link in the footer.
        """
        self.click(*self.SOCIAL_FACEBOOK)

    def click_linkedin_link(self) -> None:
        """
        Click the LinkedIn social media link in the footer.
        """
        self.click(*self.SOCIAL_LINKEDIN)

    def get_footer_text(self) -> str:
        """
        Get the footer copyright text.
        
        Returns:
            str: The footer copyright text.
        """
        return self.get_element_text(*self.FOOTER_COPY)