"""Base Page Object class for all page objects."""

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class BasePage:
    """Base class for all Page Objects."""
    
    def __init__(self, driver: WebDriver, base_url: str = ""):
        self.driver = driver
        self.base_url = base_url
        self.wait = WebDriverWait(driver, 10)
    
    def navigate(self, path: str = ""):
        """Navigate to a URL path."""
        url = f"{self.base_url}{path}"
        self.driver.get(url)
    
    def find_element(self, by: By, value: str) -> WebElement:
        """Find an element with explicit wait."""
        return self.wait.until(
            EC.presence_of_element_located((by, value))
        )
    
    def find_element_clickable(self, by: By, value: str) -> WebElement:
        """Find a clickable element with explicit wait."""
        return self.wait.until(
            EC.element_to_be_clickable((by, value))
        )
    
    def find_element_visible(self, by: By, value: str) -> WebElement:
        """Find a visible element with explicit wait."""
        return self.wait.until(
            EC.visibility_of_element_located((by, value))
        )
    
    def get_element_text(self, by: By, value: str) -> str:
        """Get text from an element."""
        element = self.find_element_visible(by, value)
        return element.text
    
    def is_element_present(self, by: By, value: str, timeout: int = 5) -> bool:
        """Check if an element is present."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except:
            return False
    
    def enter_text(self, by: By, value: str, text: str):
        """Clear and enter text into an input field."""
        element = self.find_element_visible(by, value)
        element.clear()
        element.send_keys(text)
    
    def click(self, by: By, value: str):
        """Click on an element."""
        element = self.find_element_clickable(by, value)
        element.click()
