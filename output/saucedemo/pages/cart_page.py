"""
Cart Page Object Model for Sauce Demo application.
"""

from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class CartPage(BasePage):
    """Page object for the Cart page."""

    # Locators
    HEADER_CONTAINER = (By.CSS_SELECTOR, "[data-test='header-container']")
    PRIMARY_HEADER = (By.CSS_SELECTOR, "[data-test='primary-header']")
    REACT_BURGER_MENU_BTN = (By.CSS_SELECTOR, "[data-test='react-burger-menu-btn']")
    OPEN_MENU = (By.CSS_SELECTOR, "[data-test='open-menu']")
    SHOPPING_CART_LINK = (By.CSS_SELECTOR, "[data-test='shopping-cart-link']")
    SECONDARY_HEADER = (By.CSS_SELECTOR, "[data-test='secondary-header']")
    TITLE = (By.CSS_SELECTOR, "[data-test='title']")
    ACTIVE_OPTION = (By.CSS_SELECTOR, "[data-test='active-option']")
    PRODUCT_SORT_CONTAINER = (By.CSS_SELECTOR, "[data-test='product-sort-container']")
    INVENTORY_CONTAINER = (By.CSS_SELECTOR, "[data-test='inventory-container']")
    INVENTORY_LIST = (By.CSS_SELECTOR, "[data-test='inventory-list']")
    INVENTORY_ITEM = (By.CSS_SELECTOR, "[data-test='inventory-item']")
    ITEM_4_IMG_LINK = (By.CSS_SELECTOR, "[data-test='item-4-img-link']")
    INVENTORY_ITEM_SAUCE_LABS_BACKPACK_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-backpack-img']")
    INVENTORY_ITEM_DESCRIPTION = (By.CSS_SELECTOR, "[data-test='inventory-item-description']")
    ITEM_4_TITLE_LINK = (By.CSS_SELECTOR, "[data-test='item-4-title-link']")
    INVENTORY_ITEM_NAME = (By.CSS_SELECTOR, "[data-test='inventory-item-name']")
    INVENTORY_ITEM_DESC = (By.CSS_SELECTOR, "[data-test='inventory-item-desc']")
    INVENTORY_ITEM_PRICE = (By.CSS_SELECTOR, "[data-test='inventory-item-price']")
    ADD_TO_CART_SAUCE_LABS_BACKPACK = (By.CSS_SELECTOR, "[data-test='add-to-cart-sauce-labs-backpack']")
    ITEM_0_IMG_LINK = (By.CSS_SELECTOR, "[data-test='item-0-img-link']")
    INVENTORY_ITEM_SAUCE_LABS_BIKE_LIGHT_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-bike-light-img']")
    ITEM_0_TITLE_LINK = (By.CSS_SELECTOR, "[data-test='item-0-title-link']")
    ADD_TO_CART_SAUCE_LABS_BIKE_LIGHT = (By.CSS_SELECTOR, "[data-test='add-to-cart-sauce-labs-bike-light']")
    ITEM_1_IMG_LINK = (By.CSS_SELECTOR, "[data-test='item-1-img-link']")
    INVENTORY_ITEM_SAUCE_LABS_BOLT_T_SHIRT_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-bolt-t-shirt-img']")
    ITEM_1_TITLE_LINK = (By.CSS_SELECTOR, "[data-test='item-1-title-link']")
    ADD_TO_CART_SAUCE_LABS_BOLT_T_SHIRT = (By.CSS_SELECTOR, "[data-test='add-to-cart-sauce-labs-bolt-t-shirt']")
    ITEM_5_IMG_LINK = (By.CSS_SELECTOR, "[data-test='item-5-img-link']")
    INVENTORY_ITEM_SAUCE_LABS_FLEECE_JACKET_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-fleece-jacket-img']")
    ITEM_5_TITLE_LINK = (By.CSS_SELECTOR, "[data-test='item-5-title-link']")
    ADD_TO_CART_SAUCE_LABS_FLEECE_JACKET = (By.CSS_SELECTOR, "[data-test='add-to-cart-sauce-labs-fleece-jacket']")
    ITEM_2_IMG_LINK = (By.CSS_SELECTOR, "[data-test='item-2-img-link']")
    INVENTORY_ITEM_SAUCE_LABS_ONESIE_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-sauce-labs-onesie-img']")
    ITEM_2_TITLE_LINK = (By.CSS_SELECTOR, "[data-test='item-2-title-link']")
    ADD_TO_CART_SAUCE_LABS_ONESIE = (By.CSS_SELECTOR, "[data-test='add-to-cart-sauce-labs-onesie']")
    ITEM_3_IMG_LINK = (By.CSS_SELECTOR, "[data-test='item-3-img-link']")
    INVENTORY_ITEM_TEST_ALLTHETHINGS_T_SHIRT_RED_IMG = (By.CSS_SELECTOR, "[data-test='inventory-item-test.allthethings()-t-shirt-(red)-img']")
    ITEM_3_TITLE_LINK = (By.CSS_SELECTOR, "[data-test='item-3-title-link']")
    ADD_TO_CART_TEST_ALLTHETHINGS_T_SHIRT_RED = (By.CSS_SELECTOR, "[data-test='add-to-cart-test.allthethings()-t-shirt-(red)']")
    FOOTER = (By.CSS_SELECTOR, "[data-test='footer']")
    SOCIAL_TWITTER = (By.CSS_SELECTOR, "[data-test='social-twitter']")
    SOCIAL_FACEBOOK = (By.CSS_SELECTOR, "[data-test='social-facebook']")
    SOCIAL_LINKEDIN = (By.CSS_SELECTOR, "[data-test='social-linkedin']")
    FOOTER_COPY = (By.CSS_SELECTOR, "[data-test='footer-copy']")
    
    # Cart-specific locators
    CART_ITEM = (By.CSS_SELECTOR, ".cart_item")
    CART_ITEM_NAME = (By.CSS_SELECTOR, ".inventory_item_name")
    CART_ITEM_PRICE = (By.CSS_SELECTOR, ".inventory_item_price")
    CART_QUANTITY = (By.CSS_SELECTOR, ".cart_quantity")
    REMOVE_BUTTON = (By.CSS_SELECTOR, "button[data-test^='remove-']")
    CHECKOUT_BUTTON = (By.CSS_SELECTOR, "[data-test='checkout']")
    CONTINUE_SHOPPING_BUTTON = (By.CSS_SELECTOR, "[data-test='continue-shopping']")
    CART_BADGE = (By.CSS_SELECTOR, ".shopping_cart_badge")

    def __init__(self, driver):
        """
        Initialize the CartPage.
        
        Args:
            driver: WebDriver instance
        """
        super().__init__(driver)

    # Element Getters
    def get_header_container(self):
        """Get the header container element."""
        return self.find_element_visible(self.HEADER_CONTAINER[0], self.HEADER_CONTAINER[1])

    def get_primary_header(self):
        """Get the primary header element."""
        return self.find_element_visible(self.PRIMARY_HEADER[0], self.PRIMARY_HEADER[1])

    def get_react_burger_menu_btn(self):
        """Get the burger menu button element."""
        return self.find_element_clickable(self.REACT_BURGER_MENU_BTN[0], self.REACT_BURGER_MENU_BTN[1])

    def get_open_menu(self):
        """Get the open menu element."""
        return self.find_element_visible(self.OPEN_MENU[0], self.OPEN_MENU[1])

    def get_shopping_cart_link(self):
        """Get the shopping cart link element."""
        return self.find_element_clickable(self.SHOPPING_CART_LINK[0], self.SHOPPING_CART_LINK[1])

    def get_secondary_header(self):
        """Get the secondary header element."""
        return self.find_element_visible(self.SECONDARY_HEADER[0], self.SECONDARY_HEADER[1])

    def get_title(self):
        """Get the title element."""
        return self.find_element_visible(self.TITLE[0], self.TITLE[1])

    def get_active_option(self):
        """Get the active option element."""
        return self.find_element_visible(self.ACTIVE_OPTION[0], self.ACTIVE_OPTION[1])

    def get_product_sort_container(self):
        """Get the product sort container element."""
        return self.find_element_visible(self.PRODUCT_SORT_CONTAINER[0], self.PRODUCT_SORT_CONTAINER[1])

    def get_inventory_container(self):
        """Get the inventory container element."""
        return self.find_element_visible(self.INVENTORY_CONTAINER[0], self.INVENTORY_CONTAINER[1])

    def get_inventory_list(self):
        """Get the inventory list element."""
        return self.find_element_visible(self.INVENTORY_LIST[0], self.INVENTORY_LIST[1])

    def get_inventory_items(self):
        """Get all inventory item elements."""
        return self.driver.find_elements(self.INVENTORY_ITEM[0], self.INVENTORY_ITEM[1])

    def get_footer(self):
        """Get the footer element."""
        return self.find_element_visible(self.FOOTER[0], self.FOOTER[1])

    def get_social_twitter(self):
        """Get the Twitter social link element."""
        return self.find_element_visible(self.SOCIAL_TWITTER[0], self.SOCIAL_TWITTER[1])

    def get_social_facebook(self):
        """Get the Facebook social link element."""
        return self.find_element_visible(self.SOCIAL_FACEBOOK[0], self.SOCIAL_FACEBOOK[1])

    def get_social_linkedin(self):
        """Get the LinkedIn social link element."""
        return self.find_element_visible(self.SOCIAL_LINKEDIN[0], self.SOCIAL_LINKEDIN[1])

    def get_footer_copy(self):
        """Get the footer copy element."""
        return self.find_element_visible(self.FOOTER_COPY[0], self.FOOTER_COPY[1])

    def get_checkout_button(self):
        """Get the checkout button element."""
        return self.find_element_clickable(self.CHECKOUT_BUTTON[0], self.CHECKOUT_BUTTON[1])

    def get_continue_shopping_button(self):
        """Get the continue shopping button element."""
        return self.find_element_clickable(self.CONTINUE_SHOPPING_BUTTON[0], self.CONTINUE_SHOPPING_BUTTON[1])

    # Action Methods
    def is_on_cart_page(self):
        """
        Check if the user is on the cart page.
        
        Returns:
            bool: True if on cart page, False otherwise
        """
        try:
            title_element = self.get_title()
            return title_element.text.lower() == "your cart"
        except Exception:
            return False

    def get_page_title(self):
        """
        Get the page title text.
        
        Returns:
            str: The page title text
        """
        title_element = self.get_title()
        return title_element.text

    def get_cart_items(self):
        """
        Get all cart item elements.
        
        Returns:
            list: List of cart item WebElements
        """
        try:
            return self.driver.find_elements(self.CART_ITEM[0], self.CART_ITEM[1])
        except Exception:
            return []

    def get_cart_item_count(self):
        """
        Get the number of items in the cart.
        
        Returns:
            int: Number of items in cart
        """
        cart_items = self.get_cart_items()
        return len(cart_items)

    def remove_item(self, item_name):
        """
        Remove an item from the cart by its name.
        
        Args:
            item_name: The name of the item to remove
            
        Returns:
            bool: True if item was removed, False otherwise
        """
        try:
            cart_items = self.get_cart_items()
            for item in cart_items:
                name_element = item.find_element(*self.CART_ITEM_NAME)
                if name_element.text.lower() == item_name.lower():
                    remove_button = item.find_element(*self.REMOVE_BUTTON)
                    remove_button.click()
                    return True
            return False
        except Exception:
            return False

    def click_checkout(self):
        """
        Click the checkout button to proceed to checkout.
        
        Returns:
            None
        """
        checkout_button = self.get_checkout_button()
        checkout_button.click()

    def click_continue_shopping(self):
        """
        Click the continue shopping button to return to inventory.
        
        Returns:
            None
        """
        continue_button = self.get_continue_shopping_button()
        continue_button.click()

    def is_cart_empty(self):
        """
        Check if the cart is empty.
        
        Returns:
            bool: True if cart is empty, False otherwise
        """
        return self.get_cart_item_count() == 0

    # Additional helper methods
    def click_burger_menu(self):
        """Click the burger menu button."""
        burger_btn = self.get_react_burger_menu_btn()
        burger_btn.click()

    def click_shopping_cart(self):
        """Click the shopping cart link."""
        cart_link = self.get_shopping_cart_link()
        cart_link.click()

    def get_cart_badge_count(self):
        """
        Get the count displayed on the cart badge.
        
        Returns:
            int: Number displayed on cart badge, 0 if no badge
        """
        try:
            badge = self.find_element_visible(self.CART_BADGE[0], self.CART_BADGE[1])
            return int(badge.text)
        except Exception:
            return 0

    def get_item_names_in_cart(self):
        """
        Get all item names in the cart.
        
        Returns:
            list: List of item name strings
        """
        cart_items = self.get_cart_items()
        names = []
        for item in cart_items:
            try:
                name_element = item.find_element(*self.CART_ITEM_NAME)
                names.append(name_element.text)
            except Exception:
                continue
        return names

    def get_item_prices_in_cart(self):
        """
        Get all item prices in the cart.
        
        Returns:
            list: List of item price strings
        """
        cart_items = self.get_cart_items()
        prices = []
        for item in cart_items:
            try:
                price_element = item.find_element(*self.CART_ITEM_PRICE)
                prices.append(price_element.text)
            except Exception:
                continue
        return prices

    def remove_all_items(self):
        """
        Remove all items from the cart.
        
        Returns:
            bool: True if all items were removed successfully
        """
        try:
            while not self.is_cart_empty():
                cart_items = self.get_cart_items()
                if cart_items:
                    remove_button = cart_items[0].find_element(*self.REMOVE_BUTTON)
                    remove_button.click()
                else:
                    break
            return self.is_cart_empty()
        except Exception:
            return False