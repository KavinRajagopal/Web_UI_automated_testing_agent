"""
Login Page Object Model for Selenium automation.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from pages.base_page import BasePage


class LoginPage(BasePage):
    """Page Object for the Login page."""

    # Page URL - SauceDemo uses root URL for login, not /login
    URL = ""

    # Element Locators - Updated for SauceDemo
    USERNAME_INPUT = (By.ID, "user-name")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "login-button")
    ERROR_MESSAGE = (By.CSS_SELECTOR, "[data-test='error']")
    PAGE_TITLE = (By.CLASS_NAME, "login_logo")

    def navigate(self) -> "LoginPage":
        """
        Navigate to the login page.
        
        Returns:
            LoginPage: Returns self for method chaining.
        """
        self.driver.get(self.base_url + self.URL)
        return self

    # Getter methods for elements
    @property
    def username_input(self) -> WebElement:
        """Get the username input element."""
        return self.find_element_visible(*self.USERNAME_INPUT)

    @property
    def password_input(self) -> WebElement:
        """Get the password input element."""
        return self.find_element_visible(*self.PASSWORD_INPUT)

    @property
    def login_button(self) -> WebElement:
        """Get the login button element."""
        return self.find_element_clickable(*self.LOGIN_BUTTON)

    @property
    def error_message_element(self) -> WebElement:
        """Get the error message element."""
        return self.find_element_visible(*self.ERROR_MESSAGE)

    @property
    def page_title_element(self) -> WebElement:
        """Get the page title element."""
        return self.find_element_visible(*self.PAGE_TITLE)

    # Action methods
    def enter_username(self, username: str) -> "LoginPage":
        """
        Enter username into the username input field.

        Args:
            username: The username to enter.

        Returns:
            LoginPage: Returns self for method chaining.
        """
        self.enter_text(*self.USERNAME_INPUT, username)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """
        Enter password into the password input field.

        Args:
            password: The password to enter.

        Returns:
            LoginPage: Returns self for method chaining.
        """
        self.enter_text(*self.PASSWORD_INPUT, password)
        return self

    def click_login(self) -> None:
        """
        Click the login button to submit the login form.
        """
        self.click(*self.LOGIN_BUTTON)

    def get_error_message(self) -> str:
        """
        Get the text of the error message displayed on the page.

        Returns:
            str: The error message text.
        """
        return self.get_element_text(*self.ERROR_MESSAGE)

    def is_error_displayed(self) -> bool:
        """
        Check if an error message is currently displayed on the page.

        Returns:
            bool: True if error message is displayed, False otherwise.
        """
        return self.is_element_present(*self.ERROR_MESSAGE)

    def clear_username(self) -> "LoginPage":
        """
        Clear the username input field.

        Returns:
            LoginPage: Returns self for method chaining.
        """
        self.username_input.clear()
        return self

    def clear_password(self) -> "LoginPage":
        """
        Clear the password input field.

        Returns:
            LoginPage: Returns self for method chaining.
        """
        self.password_input.clear()
        return self

    def login(self, username: str, password: str) -> None:
        """
        Perform a complete login action with the provided credentials.

        Args:
            username: The username to login with.
            password: The password to login with.
        """
        self.clear_username()
        self.enter_username(username)
        self.clear_password()
        self.enter_password(password)
        self.click_login()

    def is_on_login_page(self) -> bool:
        """
        Verify that the current page is the login page.

        Returns:
            bool: True if on login page, False otherwise.
        """
        return (
            self.is_element_present(*self.USERNAME_INPUT) and
            self.is_element_present(*self.PASSWORD_INPUT) and
            self.is_element_present(*self.LOGIN_BUTTON)
        )

    def is_page_loaded(self) -> bool:
        """
        Check if the login page is fully loaded.

        Returns:
            bool: True if page is loaded, False otherwise.
        """
        # First navigate to the page
        current_url = self.driver.current_url
        if "saucedemo" not in current_url.lower():
            self.navigate()
        
        return self.is_on_login_page()

    def is_title_displayed(self) -> bool:
        """
        Check if the page title is displayed.

        Returns:
            bool: True if title is displayed, False otherwise.
        """
        return self.is_element_present(*self.PAGE_TITLE)

    def get_title_text(self) -> str:
        """
        Get the text of the page title.

        Returns:
            str: The page title text.
        """
        return self.get_element_text(*self.PAGE_TITLE)

    def get_page_title(self) -> str:
        """
        Get the text of the page title (alias for get_title_text).

        Returns:
            str: The page title text.
        """
        return self.get_title_text()

    def is_on_page(self) -> bool:
        """
        Verify that the browser is on this page.

        Returns:
            bool: True if on this page, False otherwise.
        """
        return self.is_on_login_page()