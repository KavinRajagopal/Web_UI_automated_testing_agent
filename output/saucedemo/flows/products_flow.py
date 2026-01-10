"""Flow class for ProductsFlow."""
            
from pages.productspage import ProductsPage
from pages.cartpage import CartPage


class ProductsFlow:
    """Helper class for Product browsing and sorting flow helpers."""
    
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        # Initialize page objects
        self.productspage = ProductsPage(driver, base_url)
        self.cartpage = CartPage(driver, base_url)