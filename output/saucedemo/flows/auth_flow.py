"""Flow class for AuthFlow."""

from pages.loginpage_page import LoginPagePage
from pages.productspage_page import ProductsPagePage


class AuthFlow:
    """Helper class for Authentication flow helpers for login, logout, and credential validation scenarios."""

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
