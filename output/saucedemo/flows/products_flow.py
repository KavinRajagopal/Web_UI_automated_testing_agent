"""Flow class for ProductsFlow."""

from pages.productspage_page import ProductsPagePage
from pages.cartpage_page import CartPagePage


class ProductsFlow:
    """Helper class for Product browsing and sorting flow helpers for inventory management scenarios."""

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
