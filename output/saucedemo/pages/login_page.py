"""
Login Page Object Model for Sauce Demo application.
"""

from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class LoginPage(BasePage):
    """Page Object class for the Login Page."""

    # Element Locators
    LOGIN_CONTAINER = (By.CSS_SELECTOR, "[data-test='login-container']")
    USERNAME_INPUT = (By.CSS_SELECTOR, "[data-test='username']")
    PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-test='password']")
    LOGIN_BUTTON = (By.CSS_SELECTOR, "[data-test='login-button']")
    LOGIN_CREDENTIALS_CONTAINER = (By.CSS_SELECTOR, "[data-test='login-credentials-container']")
    LOGIN_CREDENTIALS = (By.CSS_SELECTOR, "[data-test='login-credentials']")
    LOGIN_PASSWORD = (By.CSS_SELECTOR, "[data-test='login-password']")
    ERROR_MESSAGE = (By.CSS_SELECTOR, "[data-test='error']")

    def __init__(self, driver):
        """
        Initialize the LoginPage.

        Args:
            driver: WebDriver instance
        """
        super().__init__(driver)

    # Getter methods for elements
    def get_login_container(self):
        """
        Get the login container element.

        Returns:
            WebElement: The login container element
        """
        return self.find_element_visible(self.LOGIN_CONTAINER[0], self.LOGIN_CONTAINER[1])

    def get_username_input(self):
        """
        Get the username input element.

        Returns:
            WebElement: The username input element
        """
        return self.find_element_visible(self.USERNAME_INPUT[0], self.USERNAME_INPUT[1])

    def get_password_input(self):
        """
        Get the password input element.

        Returns:
            WebElement: The password input element
        """
        return self.find_element_visible(self.PASSWORD_INPUT[0], self.PASSWORD_INPUT[1])

    def get_login_button(self):
        """
        Get the login button element.

        Returns:
            WebElement: The login button element
        """
        return self.find_element_clickable(self.LOGIN_BUTTON[0], self.LOGIN_BUTTON[1])

    def get_login_credentials_container(self):
        """
        Get the login credentials container element.

        Returns:
            WebElement: The login credentials container element
        """
        return self.find_element_visible(self.LOGIN_CREDENTIALS_CONTAINER[0], self.LOGIN_CREDENTIALS_CONTAINER[1])

    def get_login_credentials(self):
        """
        Get the login credentials element.

        Returns:
            WebElement: The login credentials element
        """
        return self.find_element_visible(self.LOGIN_CREDENTIALS[0], self.LOGIN_CREDENTIALS[1])

    def get_login_password_element(self):
        """
        Get the login password element.

        Returns:
            WebElement: The login password element
        """
        return self.find_element_visible(self.LOGIN_PASSWORD[0], self.LOGIN_PASSWORD[1])

    def get_error_element(self):
        """
        Get the error message element.

        Returns:
            WebElement: The error message element
        """
        return self.find_element_visible(self.ERROR_MESSAGE[0], self.ERROR_MESSAGE[1])

    # Action methods
    def enter_username(self, username):
        """
        Enter username into the username input field.

        Args:
            username (str): The username to enter
        """
        username_input = self.get_username_input()
        username_input.clear()
        username_input.send_keys(username)

    def enter_password(self, password):
        """
        Enter password into the password input field.

        Args:
            password (str): The password to enter
        """
        password_input = self.get_password_input()
        password_input.clear()
        password_input.send_keys(password)

    def click_login(self):
        """
        Click the login button.
        """
        login_button = self.get_login_button()
        login_button.click()

    def get_error_message(self):
        """
        Get the error message text displayed on the page.

        Returns:
            str: The error message text
        """
        error_element = self.get_error_element()
        return error_element.text

    def is_error_displayed(self):
        """
        Check if an error message is displayed on the page.

        Returns:
            bool: True if error is displayed, False otherwise
        """
        return self.is_element_present(self.ERROR_MESSAGE[0], self.ERROR_MESSAGE[1])

    def clear_username(self):
        """
        Clear the username input field.
        """
        username_input = self.get_username_input()
        username_input.clear()

    def clear_password(self):
        """
        Clear the password input field.
        """
        password_input = self.get_password_input()
        password_input.clear()

    def login(self, username, password):
        """
        Perform login action with provided credentials.

        Args:
            username (str): The username to enter
            password (str): The password to enter
        """
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()

    def is_on_login_page(self):
        """
        Check if currently on the login page.

        Returns:
            bool: True if on login page, False otherwise
        """
        return self.is_element_present(self.LOGIN_CONTAINER[0], self.LOGIN_CONTAINER[1])