"""Flow class for ProductsFlow."""

from pages.loginpage_page import LoginPagePage
from pages.productspage_page import ProductsPagePage


class ProductsFlow:
    """Helper class for Product browsing and sorting flow helpers."""

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
