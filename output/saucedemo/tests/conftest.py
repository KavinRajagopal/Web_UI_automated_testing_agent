"""Pytest fixtures for saucedemo tests."""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    return "https://www.saucedemo.com"


@pytest.fixture(scope="function")
def driver(request):
    """Chrome WebDriver fixture.
    
    To run with visible browser (default for debugging):
        pytest tests/ -v
    
    To run in headless mode:
        HEADLESS=true pytest tests/ -v
        OR
        pytest --headless=true tests/ -v
    """
    options = Options()
    
    # Check for headless setting (default: False - show browser for debugging)
    headless = request.config.getoption("--headless", default=None)
    if headless is None:
        # Check environment variable (defaults to False - visible browser)
        headless = os.getenv("HEADLESS", "false").lower() == "true"
    else:
        headless = headless.lower() == "true"
    
    if headless:
        options.add_argument("--headless=new")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Start maximized for better visibility when not headless
    if not headless:
        options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    
    yield driver
    
    driver.quit()


def pytest_addoption(parser):
    """Add custom pytest command line options."""
    parser.addoption(
        "--headless",
        action="store",
        default=None,
        help="Run browser in headless mode: --headless=true or --headless=false (default: false - visible browser)"
    )





