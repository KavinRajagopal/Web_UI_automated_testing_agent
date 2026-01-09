"""
Page Object Model for Products Page
File: pages/products_page.py
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from pages.base_page import BasePage


class ProductsPage(BasePage):
    """Page Object for the Products/Inventory page."""

    # Element Locators
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

    # Product add to cart button mapping
    PRODUCT_ADD_TO_CART_BUTTONS = {
        "sauce labs backpack": ADD_TO_CART_SAUCE_LABS_BACKPACK,
        "sauce labs bike light": ADD_TO_CART_SAUCE_LABS_BIKE_LIGHT,
        "sauce labs bolt t-shirt": ADD_TO_CART_SAUCE_LABS_BOLT_T_SHIRT,
        "sauce labs fleece jacket": ADD_TO_CART_SAUCE_LABS_FLEECE_JACKET,
        "sauce labs onesie": ADD_TO_CART_SAUCE_LABS_ONESIE,
        "test.allthethings() t-shirt (red)": ADD_TO_CART_TEST_ALLTHETHINGS_T_SHIRT_RED,
    }

    def __init__(self, driver):
        """
        Initialize the ProductsPage.

        Args:
            driver: WebDriver instance
        """
        super().__init__(driver)

    # Getter methods for elements
    def get_header_container(self):
        """
        Get the header container element.

        Returns:
            WebElement: The header container element
        """
        return self.find_element_visible(self.HEADER_CONTAINER[0], self.HEADER_CONTAINER[1])

    def get_primary_header(self):
        """
        Get the primary header element.

        Returns:
            WebElement: The primary header element
        """
        return self.find_element_visible(self.PRIMARY_HEADER[0], self.PRIMARY_HEADER[1])

    def get_react_burger_menu_btn(self):
        """
        Get the burger menu button element.

        Returns:
            WebElement: The burger menu button element
        """
        return self.find_element_clickable(self.REACT_BURGER_MENU_BTN[0], self.REACT_BURGER_MENU_BTN[1])

    def get_shopping_cart_link(self):
        """
        Get the shopping cart link element.

        Returns:
            WebElement: The shopping cart link element
        """
        return self.find_element_clickable(self.SHOPPING_CART_LINK[0], self.SHOPPING_CART_LINK[1])

    def get_secondary_header(self):
        """
        Get the secondary header element.

        Returns:
            WebElement: The secondary header element
        """
        return self.find_element_visible(self.SECONDARY_HEADER[0], self.SECONDARY_HEADER[1])

    def get_title_element(self):
        """
        Get the title element.

        Returns:
            WebElement: The title element
        """
        return self.find_element_visible(self.TITLE[0], self.TITLE[1])

    def get_active_option_element(self):
        """
        Get the active sort option element.

        Returns:
            WebElement: The active sort option element
        """
        return self.find_element_visible(self.ACTIVE_OPTION[0], self.ACTIVE_OPTION[1])

    def get_product_sort_container(self):
        """
        Get the product sort container/dropdown element.

        Returns:
            WebElement: The product sort container element
        """
        return self.find_element_clickable(self.PRODUCT_SORT_CONTAINER[0], self.PRODUCT_SORT_CONTAINER[1])

    def get_inventory_container(self):
        """
        Get the inventory container element.

        Returns:
            WebElement: The inventory container element
        """
        return self.find_element_visible(self.INVENTORY_CONTAINER[0], self.INVENTORY_CONTAINER[1])

    def get_inventory_list(self):
        """
        Get the inventory list element.

        Returns:
            WebElement: The inventory list element
        """
        return self.find_element_visible(self.INVENTORY_LIST[0], self.INVENTORY_LIST[1])

    def get_inventory_items(self):
        """
        Get all inventory item elements.

        Returns:
            list: List of inventory item WebElements
        """
        # Wait for at least one item to be visible, then get all
        self.find_element_visible(self.INVENTORY_ITEM[0], self.INVENTORY_ITEM[1])
        return self.driver.find_elements(self.INVENTORY_ITEM[0], self.INVENTORY_ITEM[1])

    def get_footer(self):
        """
        Get the footer element.

        Returns:
            WebElement: The footer element
        """
        return self.find_element_visible(self.FOOTER[0], self.FOOTER[1])

    def get_social_twitter_link(self):
        """
        Get the Twitter social link element.

        Returns:
            WebElement: The Twitter link element
        """
        return self.find_element_clickable(self.SOCIAL_TWITTER[0], self.SOCIAL_TWITTER[1])

    def get_social_facebook_link(self):
        """
        Get the Facebook social link element.

        Returns:
            WebElement: The Facebook link element
        """
        return self.find_element_clickable(self.SOCIAL_FACEBOOK[0], self.SOCIAL_FACEBOOK[1])

    def get_social_linkedin_link(self):
        """
        Get the LinkedIn social link element.

        Returns:
            WebElement: The LinkedIn link element
        """
        return self.find_element_clickable(self.SOCIAL_LINKEDIN[0], self.SOCIAL_LINKEDIN[1])

    def get_footer_copy(self):
        """
        Get the footer copy/copyright element.

        Returns:
            WebElement: The footer copy element
        """
        return self.find_element_visible(self.FOOTER_COPY[0], self.FOOTER_COPY[1])

    # Action methods
    def is_on_products_page(self):
        """
        Check if the user is on the products page.

        Returns:
            bool: True if on products page, False otherwise
        """
        try:
            title_element = self.get_title_element()
            return title_element.is_displayed() and "Products" in title_element.text
        except Exception:
            return False

    def get_page_title(self):
        """
        Get the page title text.

        Returns:
            str: The page title text
        """
        return self.get_title_element().text

    def is_inventory_displayed(self):
        """
        Check if the inventory/products list is displayed.

        Returns:
            bool: True if inventory is displayed, False otherwise
        """
        try:
            inventory = self.get_inventory_container()
            return inventory.is_displayed()
        except Exception:
            return False

    def get_product_count(self):
        """
        Get the count of products displayed on the page.

        Returns:
            int: Number of products displayed
        """
        items = self.get_inventory_items()
        return len(items)

    def get_product_names(self):
        """
        Get a list of all product names displayed on the page.

        Returns:
            list: List of product name strings
        """
        items = self.get_inventory_items()
        names = []
        for item in items:
            name_element = item.find_element(*self.INVENTORY_ITEM_NAME)
            names.append(name_element.text)
        return names

    def get_product_prices(self):
        """
        Get a list of all product prices displayed on the page.

        Returns:
            list: List of product price strings
        """
        items = self.get_inventory_items()
        prices = []
        for item in items:
            price_element = item.find_element(*self.INVENTORY_ITEM_PRICE)
            prices.append(price_element.text)
        return prices

    def add_product_to_cart(self, product_name):
        """
        Add a product to the cart by its name.

        Args:
            product_name: The name of the product to add (case-insensitive)

        Returns:
            bool: True if product was added successfully, False otherwise
        """
        product_name_lower = product_name.lower()
        
        if product_name_lower in self.PRODUCT_ADD_TO_CART_BUTTONS:
            locator = self.PRODUCT_ADD_TO_CART_BUTTONS[product_name_lower]
            button = self.find_element_clickable(locator[0], locator[1])
            button.click()
            return True
        
        # Fallback: try to find the button dynamically
        items = self.get_inventory_items()
        for item in items:
            name_element = item.find_element(*self.INVENTORY_ITEM_NAME)
            if name_element.text.lower() == product_name_lower:
                add_button = item.find_element(By.CSS_SELECTOR, "button[data-test^='add-to-cart']")
                add_button.click()
                return True
        
        return False

    def open_burger_menu(self):
        """
        Open the burger/hamburger menu.

        Returns:
            ProductsPage: Self for method chaining
        """
        burger_btn = self.get_react_burger_menu_btn()
        burger_btn.click()
        return self

    def click_shopping_cart(self):
        """
        Click on the shopping cart link.

        Returns:
            ProductsPage: Self for method chaining
        """
        cart_link = self.get_shopping_cart_link()
        cart_link.click()
        return self

    def select_sort_option(self, option_value):
        """
        Select a sort option from the product sort dropdown.

        Args:
            option_value: The value of the sort option to select
                         (e.g., 'az', 'za', 'lohi', 'hilo')

        Returns:
            ProductsPage: Self for method chaining
        """
        sort_dropdown = self.get_product_sort_container()
        select = Select(sort_dropdown)
        select.select_by_value(option_value)
        return self

    def get_active_sort_option(self):
        """
        Get the currently active/selected sort option text.

        Returns:
            str: The text of the active sort option
        """
        active_option = self.get_active_option_element()
        return active_option.text

    def get_products_in_display_order(self):
        """
        Get all products in their current display order with name and price.

        Returns:
            list: List of dictionaries containing product info
                  [{'name': str, 'price': str, 'description': str}, ...]
        """
        items = self.get_inventory_items()
        products = []
        
        for item in items:
            name_element = item.find_element(*self.INVENTORY_ITEM_NAME)
            price_element = item.find_element(*self.INVENTORY_ITEM_PRICE)
            desc_element = item.find_element(*self.INVENTORY_ITEM_DESC)
            
            products.append({
                'name': name_element.text,
                'price': price_element.text,
                'description': desc_element.text
            })
        
        return products