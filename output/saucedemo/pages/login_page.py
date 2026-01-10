"""
LoginPage - Page Object for Login Page
Generated using Selenium WebDriver
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from pages.base_page import BasePage


class LoginPage(BasePage):
    """Page Object for the Login Page."""

    # Page URL
    PAGE_URL = "/login"

    # Element Locators - Updated to match SauceDemo actual selectors
    USERNAME_INPUT = (By.ID, "user-name")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "login-button")
    ERROR_MESSAGE = (By.CSS_SELECTOR, "[data-test='error']")
    PAGE_TITLE = (By.CSS_SELECTOR, ".login_logo")

    def __init__(self, driver):
        """
        Initialize the LoginPage.

        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    # Element Getters
    def get_username_input(self) -> WebElement:
        """
        Get the username input element.

        Returns:
            WebElement: The username input field
        """
        return self.find_element_visible(*self.USERNAME_INPUT)

    def get_password_input(self) -> WebElement:
        """
        Get the password input element.

        Returns:
            WebElement: The password input field
        """
        return self.find_element_visible(*self.PASSWORD_INPUT)

    def get_login_button(self) -> WebElement:
        """
        Get the login button element.

        Returns:
            WebElement: The login button
        """
        return self.find_element_clickable(*self.LOGIN_BUTTON)

    def get_error_message_element(self) -> WebElement:
        """
        Get the error message element.

        Returns:
            WebElement: The error message element
        """
        return self.find_element_visible(*self.ERROR_MESSAGE)

    def get_page_title_element(self) -> WebElement:
        """
        Get the page title element.

        Returns:
            WebElement: The page title element
        """
        return self.find_element_visible(*self.PAGE_TITLE)

    # Action Methods
    def enter_username(self, username: str) -> "LoginPage":
        """
        Enter text into the username field.

        Args:
            username: The username to enter

        Returns:
            LoginPage: Self for method chaining
        """
        self.enter_text(*self.USERNAME_INPUT, text=username)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """
        Enter text into the password field.

        Args:
            password: The password to enter

        Returns:
            LoginPage: Self for method chaining
        """
        self.enter_text(*self.PASSWORD_INPUT, text=password)
        return self

    def click_login_button(self) -> None:
        """
        Click the login button.
        """
        self.click(*self.LOGIN_BUTTON)

    def click_login(self) -> None:
        """
        Click the login button (alias for click_login_button).
        """
        self.click(*self.LOGIN_BUTTON)

    def login(self, username: str, password: str) -> None:
        """
        Perform a complete login action with username and password.

        Args:
            username: The username to enter
            password: The password to enter
        """
        self.enter_username(username)
        self.enter_password(password)
        self.click_login_button()

    def get_error_message(self) -> str:
        """
        Get the text of the error message.

        Returns:
            str: The error message text
        """
        return self.get_element_text(*self.ERROR_MESSAGE)

    def is_error_displayed(self) -> bool:
        """
        Check if an error message is displayed.

        Returns:
            bool: True if error message is displayed, False otherwise
        """
        return self.is_element_present(*self.ERROR_MESSAGE)

    def clear_username(self) -> "LoginPage":
        """
        Clear the username input field.

        Returns:
            LoginPage: Self for method chaining
        """
        username_input = self.get_username_input()
        username_input.clear()
        return self

    def clear_password(self) -> "LoginPage":
        """
        Clear the password input field.

        Returns:
            LoginPage: Self for method chaining
        """
        password_input = self.get_password_input()
        password_input.clear()
        return self

    def is_on_login_page(self) -> bool:
        """
        Verify that the user is on the login page.

        Returns:
            bool: True if on login page, False otherwise
        """
        return self.is_element_present(*self.LOGIN_BUTTON) and \
               self.is_element_present(*self.USERNAME_INPUT) and \
               self.is_element_present(*self.PASSWORD_INPUT)

    def is_page_loaded(self) -> bool:
        """
        Check if the login page is fully loaded.

        Returns:
            bool: True if page is loaded, False otherwise
        """
        try:
            return self.is_element_present(*self.LOGIN_BUTTON) and \
                   self.is_element_present(*self.USERNAME_INPUT) and \
                   self.is_element_present(*self.PASSWORD_INPUT)
        except Exception:
            return False

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
        Verify that the user is on this page (alias for is_on_login_page).

        Returns:
            bool: True if on login page, False otherwise
        """
        return self.is_on_login_page()