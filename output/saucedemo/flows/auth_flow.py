"""Flow class for AuthFlow."""
        
from pages.loginpage import LoginPage
from pages.productspage import ProductsPage


class AuthFlow:
    """Helper class for Authentication flow helpers for login, logout, and credential validation scenarios."""
    
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        # Initialize page objects
        self.loginpage = LoginPage(driver, base_url)
        self.productspage = ProductsPage(driver, base_url)