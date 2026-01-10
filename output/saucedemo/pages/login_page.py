"""
Login Page Object Model

This module contains the LoginPage class for interacting with the login page.
Uses Selenium WebDriver for browser automation.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from pages.base_page import BasePage


class LoginPage(BasePage):
    """
    Page Object Model for the Login Page.
    
    This class provides methods to interact with login page elements
    including username field, password field, login button, and error messages.
    """
    
    # Page URL
    PAGE_URL = "/login"
    
    # Element Locators - Updated to match actual SauceDemo page
    USERNAME_INPUT = (By.ID, "user-name")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "login-button")
    ERROR_MESSAGE = (By.CSS_SELECTOR, "[data-test='error']")
    PAGE_TITLE = (By.CLASS_NAME, "login_logo")
    LOGIN_FORM = (By.ID, "login_button_container")
    
    def __init__(self, driver):
        """
        Initialize the LoginPage.
        
        Args:
            driver: Selenium WebDriver instance
        """
        super().__init__(driver)
    
    # Element Getters
    @property
    def username_input(self) -> WebElement:
        """
        Get the username input element.
        
        Returns:
            WebElement: The username input field
        """
        return self.find_element_visible(*self.USERNAME_INPUT)
    
    @property
    def password_input(self) -> WebElement:
        """
        Get the password input element.
        
        Returns:
            WebElement: The password input field
        """
        return self.find_element_visible(*self.PASSWORD_INPUT)
    
    @property
    def login_button(self) -> WebElement:
        """
        Get the login button element.
        
        Returns:
            WebElement: The login button
        """
        return self.find_element_clickable(*self.LOGIN_BUTTON)
    
    @property
    def error_message_element(self) -> WebElement:
        """
        Get the error message element.
        
        Returns:
            WebElement: The error message element
        """
        return self.find_element_visible(*self.ERROR_MESSAGE)
    
    # Action Methods
    def enter_username(self, username: str) -> "LoginPage":
        """
        Enter text into the username field.
        
        Args:
            username: The username to enter
            
        Returns:
            LoginPage: Self reference for method chaining
        """
        self.enter_text(*self.USERNAME_INPUT, text=username)
        return self
    
    def enter_password(self, password: str) -> "LoginPage":
        """
        Enter text into the password field.
        
        Args:
            password: The password to enter
            
        Returns:
            LoginPage: Self reference for method chaining
        """
        self.enter_text(*self.PASSWORD_INPUT, text=password)
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
            str: The error message text
        """
        return self.get_element_text(*self.ERROR_MESSAGE)
    
    def is_error_displayed(self) -> bool:
        """
        Check if an error message is currently displayed.
        
        Returns:
            bool: True if error message is displayed, False otherwise
        """
        return self.is_element_present(*self.ERROR_MESSAGE)
    
    def clear_username(self) -> "LoginPage":
        """
        Clear the username input field.
        
        Returns:
            LoginPage: Self reference for method chaining
        """
        element = self.find_element_visible(*self.USERNAME_INPUT)
        element.clear()
        return self
    
    def clear_password(self) -> "LoginPage":
        """
        Clear the password input field.
        
        Returns:
            LoginPage: Self reference for method chaining
        """
        element = self.find_element_visible(*self.PASSWORD_INPUT)
        element.clear()
        return self
    
    def is_on_login_page(self) -> bool:
        """
        Verify that the browser is currently on the login page.
        
        Returns:
            bool: True if on login page, False otherwise
        """
        return self.is_element_present(*self.LOGIN_FORM)
    
    # Additional helper methods
    def is_page_loaded(self) -> bool:
        """
        Check if the login page is fully loaded.
        
        Returns:
            bool: True if page is loaded, False otherwise
        """
        return (self.is_element_present(*self.USERNAME_INPUT) and
                self.is_element_present(*self.PASSWORD_INPUT) and
                self.is_element_present(*self.LOGIN_BUTTON))
    
    def login(self, username: str, password: str) -> None:
        """
        Perform a complete login action.
        
        Args:
            username: The username to enter
            password: The password to enter
        """
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()
    
    def get_page_title(self) -> str:
        """
        Get the login page title text.
        
        Returns:
            str: The page title text
        """
        return self.get_element_text(*self.PAGE_TITLE)
    
    def is_title_displayed(self) -> bool:
        """
        Check if the page title is displayed.
        
        Returns:
            bool: True if title is displayed, False otherwise
        """
        return self.is_element_present(*self.PAGE_TITLE)
    
    def is_on_page(self) -> bool:
        """
        Verify that the browser is on the login page.
        Alias for is_on_login_page().
        
        Returns:
            bool: True if on login page, False otherwise
        """
        return self.is_on_login_page()