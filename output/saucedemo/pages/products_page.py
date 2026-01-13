"""
Products Page Object Model for Sauce Demo application.
Uses Selenium WebDriver for browser automation.
"""

from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from pages.base_page import BasePage


class ProductsPage(BasePage):
    """Page Object for the Products/Inventory page of Sauce Demo."""


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
    def __init__(self, driver):
        """
        Initialize the ProductsPage.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def is_page_loaded(self) -> bool:
        """
        Check if the Products page is fully loaded.

        Returns:
            bool: True if required elements are present, False otherwise
        """
        return self.is_element_present(*self.INVENTORY_CONTAINER, timeout=10)

    def is_on_page(self) -> bool:
        """
        Alias for is_page_loaded().

        Returns:
            bool: True if on the Products page, False otherwise
        """
        return self.is_page_loaded()

    def is_products_page_displayed(self) -> bool:
        """
        Check if the Products page is displayed.

        Returns:
            bool: True if the products page is displayed, False otherwise
        """
        return self.is_page_loaded()

    def get_page_title(self) -> str:
        """
        Get the page title text.

        Returns:
            str: The page title text
        """
        return self.get_element_text(*self.TITLE)

    def is_inventory_container_visible(self) -> bool:
        """
        Check if the inventory container is visible.

        Returns:
            bool: True if inventory container is visible, False otherwise
        """
        return self.is_element_present(*self.INVENTORY_CONTAINER, timeout=5)

    def get_product_count(self) -> int:
        """
        Get the total count of products displayed.

        Returns:
            int: Number of products on the page
        """
        products = self.driver.find_elements(*self.INVENTORY_ITEM)
        return len(products)

    def get_all_product_names(self) -> List[str]:
        """
        Get all product names displayed on the page.

        Returns:
            List[str]: List of all product names
        """
        name_elements = self.driver.find_elements(*self.INVENTORY_ITEM_NAME)
        return [element.text for element in name_elements]

    def get_all_product_prices(self) -> List[str]:
        """
        Get all product prices displayed on the page.

        Returns:
            List[str]: List of all product prices as strings
        """
        price_elements = self.driver.find_elements(*self.INVENTORY_ITEM_PRICE)
        return [element.text for element in price_elements]

    def add_product_to_cart(self, product_name: str) -> None:
        """
        Add a specific product to the cart by name.

        Args:
            product_name: Name of the product to add (e.g., 'Sauce Labs Backpack')
        """
        product_mapping = {
            "sauce labs backpack": self.ADD_TO_CART_SAUCE_LABS_BACKPACK,
            "sauce labs bike light": self.ADD_TO_CART_SAUCE_LABS_BIKE_LIGHT,
            "sauce labs bolt t-shirt": self.ADD_TO_CART_SAUCE_LABS_BOLT_T_SHIRT,
            "sauce labs fleece jacket": self.ADD_TO_CART_SAUCE_LABS_FLEECE_JACKET,
            "sauce labs onesie": self.ADD_TO_CART_SAUCE_LABS_ONESIE,
            "test.allthethings() t-shirt (red)": self.ADD_TO_CART_TEST_ALLTHETHINGS__T_SHIRT__RED,
        }

        normalized_name = product_name.lower()
        if normalized_name in product_mapping:
            locator = product_mapping[normalized_name]
            self.click(*locator)
        else:
            raise ValueError(f"Product '{product_name}' not found in product mapping")

    def click_shopping_cart(self) -> None:
        """
        Click on the shopping cart link to navigate to the cart page.
        """
        self.click(*self.SHOPPING_CART_LINK)

    def select_sort_option(self, sort_option: str) -> None:
        """
        Select a sort option from the product sort dropdown.

        Args:
            sort_option: The sort option value to select
                        (e.g., 'az', 'za', 'lohi', 'hilo')
        """
        dropdown_element = self.find_element_clickable(*self.PRODUCT_SORT_CONTAINER)
        select = Select(dropdown_element)
        select.select_by_value(sort_option)

    def get_active_sort_option(self) -> str:
        """
        Get the currently active sort option.

        Returns:
            str: The text of the currently selected sort option
        """
        return self.get_element_text(*self.ACTIVE_OPTION)

    def get_products_sorted_by_name(self, ascending: bool = True) -> List[str]:
        """
        Get product names sorted alphabetically.

        Args:
            ascending: If True, sort A-Z; if False, sort Z-A

        Returns:
            List[str]: List of product names sorted as specified
        """
        product_names = self.get_all_product_names()
        return sorted(product_names, reverse=not ascending)

    def open_burger_menu(self) -> None:
        """
        Open the burger menu by clicking the menu button.
        """
        self.click(*self.REACT_BURGER_MENU_BTN)