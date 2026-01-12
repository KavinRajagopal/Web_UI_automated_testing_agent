"""
Login Page Object Model for SauceDemo application.
Uses Selenium WebDriver for browser automation.
"""

from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class LoginPage(BasePage):
    """
    Page Object Model for the SauceDemo login page.
    Handles all login-related interactions and validations.
    """



    # Element Locators (auto-generated from metadata)
    LOGIN_CONTAINER = (By.CSS_SELECTOR, "[data-test='login-container']")
    USERNAME = (By.ID, "user-name")
    PASSWORD = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "login-button")
    LOGIN_CREDENTIALS_CONTAINER = (By.CSS_SELECTOR, "[data-test='login-credentials-container']")
    LOGIN_CREDENTIALS = (By.ID, "login_credentials")
    LOGIN_PASSWORD = (By.CSS_SELECTOR, "[data-test='login-password']")
    ERROR_MESSAGE = (By.CSS_SELECTOR, "[data-test='error']")
    # Element Locators (auto-generated from metadata)
    def __init__(self, driver):
        """
        Initialize the LoginPage with a WebDriver instance.
        
        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)

    def is_page_loaded(self) -> bool:
        """
        Check if the login page is fully loaded by verifying required elements.
        
        Returns:
            bool: True if all required elements are present, False otherwise
        """
        return (
            self.is_element_present(*self.USERNAME, timeout=10) and
            self.is_element_present(*self.PASSWORD, timeout=10) and
            self.is_element_present(*self.LOGIN_BUTTON, timeout=10)
        )

    def is_on_login_page(self) -> bool:
        """
        Alias for is_page_loaded() to check if user is on the login page.
        
        Returns:
            bool: True if on login page, False otherwise
        """
        return self.is_page_loaded()

    def is_on_page(self) -> bool:
        """
        Alias for is_page_loaded() for consistent naming convention.
        
        Returns:
            bool: True if on login page, False otherwise
        """
        return self.is_page_loaded()

    def enter_username(self, username: str) -> None:
        """
        Enter text into the username input field.
        
        Args:
            username: The username to enter
        """
        self.enter_text(*self.USERNAME, text=username)

    def enter_password(self, password: str) -> None:
        """
        Enter text into the password input field.
        
        Args:
            password: The password to enter
        """
        self.enter_text(*self.PASSWORD, text=password)

    def click_login_button(self) -> None:
        """
        Click the login button to submit credentials.
        """
        self.click(*self.LOGIN_BUTTON)

    def click_login(self) -> None:
        """
        Alias for click_login_button() for convenience.
        """
        self.click_login_button()

    def get_error_message(self) -> str:
        """
        Get the text of the error message displayed on login failure.
        
        Returns:
            str: The error message text
        """
        return self.get_element_text(*self.ERROR_MESSAGE)

    def is_error_displayed(self) -> bool:
        """
        Check if an error message is currently displayed.
        
        Returns:
            bool: True if error message is visible, False otherwise
        """
        return self.is_element_present(*self.ERROR_MESSAGE, timeout=5)

    def clear_username(self) -> None:
        """
        Clear the username input field.
        """
        element = self.find_element_visible(*self.USERNAME)
        element.clear()

    def clear_password(self) -> None:
        """
        Clear the password input field.
        """
        element = self.find_element_visible(*self.PASSWORD)
        element.clear()

    def login(self, username: str, password: str) -> None:
        """
        Perform a complete login action with provided credentials.
        
        Args:
            username: The username to login with
            password: The password to login with
        """
        self.enter_username(username)
        self.enter_password(password)
        self.click_login_button()