"""Automated test file."""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from pages.login_page import LoginPage
from pages.products_page import ProductsPage

@pytest.mark.smoke
@pytest.mark.login
@pytest.mark.positive
@pytest.mark.P0
def test_valid_login_with_standard_user(driver, base_url):
    """
    Test ID: TC_LOGIN_001
    Test Name: test_valid_login_with_standard_user
    Description: Test valid login with standard_user credentials and verify successful redirect to products page
    
    Steps:
    1. Navigate to login page
    2. Enter standard_user credentials
    3. Click login button
    4. Verify redirect to products page
    5. Verify URL contains /inventory.html
    6. Verify products title is displayed
    
    Expected Results:
    - User is redirected to products page
    - URL contains '/inventory.html'
    - Products title is displayed
    """
    # Test data
    username = "standard_user"
    password = "secret_sauce"
    
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify we are on the login page
    assert login_page.is_on_login_page(), "Failed to load login page"
    
    # Step 2: Enter standard_user credentials
    login_page.enter_username(username)
    login_page.enter_password(password)
    
    # Step 3: Click login button
    login_page.click_login_button()
    
    # Step 4: Verify redirect to products page
    assert products_page.is_page_loaded(), "Products page did not load after login"
    
    # Step 5: Verify URL contains /inventory.html
    current_url = driver.current_url
    assert "/inventory.html" in current_url, f"URL does not contain '/inventory.html'. Current URL: {current_url}"
    
    # Step 6: Verify products title is displayed
    assert products_page.is_products_page_displayed(), "Products page title is not displayed"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_password(driver, base_url):
    """
    Test ID: TC_LOGIN_002
    Test Name: test_invalid_login_with_wrong_password
    Description: Test login failure with correct username but wrong password
    
    Steps:
    1. Navigate to login page
    2. Enter standard_user username
    3. Enter wrong password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    
    Expected Results:
    - User remains on login page
    - Error message is displayed
    - Error indicates invalid credentials
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify we are on the login page
    assert login_page.is_on_login_page(), "Failed to navigate to login page"
    
    # Step 2: Enter standard_user username
    login_page.enter_username("standard_user")
    
    # Step 3: Enter wrong password
    login_page.enter_password("wrong_password")
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Verify error message indicates invalid credentials
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"
    assert "username" in error_message.lower() or "password" in error_message.lower() or "credentials" in error_message.lower() or "do not match" in error_message.lower(), \
        f"Error message should indicate invalid credentials, got: {error_message}"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_username(driver, base_url):
    """
    Test ID: TC_LOGIN_003
    Test Name: test_invalid_login_with_wrong_username
    Description: Test login failure with invalid username and correct password
    
    Steps:
    1. Navigate to login page
    2. Enter invalid username
    3. Enter correct password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    
    Expected Results:
    - User remains on login page after failed login attempt
    - Error message is displayed indicating invalid credentials
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Step 2: Enter invalid username
    invalid_username = "invalid_user_12345"
    login_page.enter_username(invalid_username)
    
    # Step 3: Enter correct password
    correct_password = "secret_sauce"
    login_page.enter_password(correct_password)
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid login"
    
    # Verify error message content
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P1
def test_login_with_locked_out_user(driver, base_url):
    """
    Test ID: TC_LOGIN_004
    Test Name: test_login_with_locked_out_user
    Description: Test that locked_out_user cannot login and receives appropriate error message
    
    Steps:
    1. Navigate to login page
    2. Enter locked_out_user credentials
    3. Click login button
    4. Verify user remains on login page
    5. Verify locked out error message is displayed
    
    Expected Results:
    - User remains on login page
    - Error message indicates user is locked out
    - Login is prevented
    """
    # Test data
    username = "locked_out_user"
    password = "secret_sauce"
    
    # Step 1: Navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Enter locked_out_user credentials
    login_page.enter_username(username)
    login_page.enter_password(password)
    
    # Step 3: Click login button
    login_page.click_login_button()
    
    # Step 4: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login attempt"
    
    # Step 5: Verify locked out error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for locked out user"
    
    # Verify the error message indicates user is locked out
    error_message = login_page.get_error_message()
    assert "locked out" in error_message.lower(), f"Error message should indicate user is locked out. Actual message: {error_message}"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_username(driver, base_url):
    """
    Test ID: TC_LOGIN_005
    Test Name: test_login_with_empty_username
    Description: Test login validation when username field is left empty
    
    Steps:
    1. Navigate to login page
    2. Leave username field empty
    3. Enter password
    4. Click login button
    5. Verify error message for required username
    
    Expected Results:
    - Error message is displayed for required username field
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify we are on the login page
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Leave username field empty (clear it to ensure it's empty)
    login_page.clear_username()
    
    # Step 3: Enter password
    login_page.enter_password("TestPassword123")
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify error message for required username
    assert login_page.is_error_displayed(), "Error message should be displayed when username is empty"
    
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_password(driver, base_url):
    """
    Test ID: TC_LOGIN_006
    Test Name: test_login_with_empty_password
    Description: Test login validation when password field is left empty
    
    Steps:
    1. Navigate to login page
    2. Enter username
    3. Leave password field empty
    4. Click login button
    5. Verify error message for required password
    
    Expected Results:
    - Error message is displayed indicating password is required
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify we are on the login page
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Step 2: Enter username
    login_page.enter_username("testuser")
    
    # Step 3: Leave password field empty (clear it to ensure it's empty)
    login_page.clear_password()
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify error message for required password
    assert login_page.is_error_displayed(), "Error message should be displayed for empty password"
    
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P2
def test_login_with_both_fields_empty(driver, base_url):
    """
    Test ID: TC_LOGIN_007
    Test Name: test_login_with_both_fields_empty
    Description: Test login validation when both username and password fields are empty
    
    Steps:
    1. Navigate to login page
    2. Leave both fields empty
    3. Click login button
    4. Verify error message is displayed
    
    Expected Results:
    - Error message should be displayed when attempting to login with empty fields
    """
    # Initialize the LoginPage
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify we are on the login page
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Leave both fields empty (clear any pre-filled values)
    login_page.clear_username()
    login_page.clear_password()
    
    # Step 3: Click login button
    login_page.click_login_button()
    
    # Step 4: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed when both fields are empty"
    
    # Verify error message content is not empty
    error_message = login_page.get_error_message()
    assert error_message, "Error message should contain text"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.edge_case
@pytest.mark.P2
def test_login_with_special_characters_in_username(driver, base_url):
    """
    Test ID: TC_LOGIN_008
    Test Name: test_login_with_special_characters_in_username
    Description: Test that application safely handles special characters and XSS attempts in username
    
    Steps:
    1. Navigate to login page
    2. Enter XSS script in username field
    3. Enter password
    4. Click login button
    5. Verify error message is displayed
    6. Verify no script execution
    
    Expected Results: Test passes - application safely handles XSS attempt
    """
    # XSS attack payloads to test
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "';alert('XSS');//",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')"
    ]
    
    # Initialize login page
    login_page = LoginPage(driver)
    
    # Navigate to login page
    driver.get(base_url)
    
    # Verify we are on the login page
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Test with XSS script in username
    xss_username = xss_payloads[0]  # Using basic script tag XSS
    test_password = "TestPassword123"
    
    # Enter XSS script in username field
    login_page.enter_username(xss_username)
    
    # Enter password
    login_page.enter_password(test_password)
    
    # Click login button
    login_page.click_login_button()
    
    # Verify error message is displayed (login should fail with invalid credentials)
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid login attempt"
    
    # Get error message to verify it's a proper error response
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"
    
    # Verify no script execution occurred by checking page is still functional
    # If XSS executed, the page state would likely be compromised
    assert login_page.is_on_login_page(), "Should still be on login page after XSS attempt - no redirect or script execution"
    
    # Verify the script tag is not rendered as executable HTML
    # Check that we can still interact with the page (no JavaScript errors from XSS)
    login_page.clear_username()
    login_page.clear_password()
    
    # Page should still be responsive after XSS attempt
    assert login_page.is_page_loaded(), "Page should remain functional after XSS attempt"

@pytest.mark.products
@pytest.mark.positive
@pytest.mark.smoke
@pytest.mark.P0
def test_view_products_list_after_login(driver, base_url):
    """
    Test ID: TC_PRODUCTS_001
    Test Name: test_view_products_list_after_login
    Description: Test that products list is displayed correctly after successful login
    
    Steps:
    1. Login as standard_user
    2. Verify products page is displayed
    3. Verify inventory container is visible
    4. Verify products are listed with names and prices
    
    Expected Results:
    - Products page is displayed
    - Title shows 'Products'
    - Multiple inventory items are visible
    - Product names and prices are displayed
    """
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Navigate to the login page
    driver.get(base_url)
    
    # Step 1: Login as standard_user
    login_page.enter_username("standard_user")
    login_page.enter_password("secret_sauce")
    login_page.click_login_button()
    
    # Step 2: Verify products page is displayed
    assert products_page.is_products_page_displayed(), "Products page should be displayed after login"
    
    # Verify title shows 'Products'
    page_title = products_page.get_page_title()
    assert page_title == "Products", f"Page title should be 'Products', but got '{page_title}'"
    
    # Step 3: Verify inventory container is visible
    assert products_page.is_inventory_container_visible(), "Inventory container should be visible"
    
    # Step 4: Verify products are listed with names and prices
    product_names = products_page.get_all_product_names()
    product_prices = products_page.get_all_product_prices()
    
    # Verify multiple inventory items are visible
    product_count = products_page.get_product_count()
    assert product_count > 0, "At least one product should be displayed"
    
    # Verify product names are displayed
    assert len(product_names) > 0, "Product names should be displayed"
    for name in product_names:
        assert name is not None and name.strip() != "", "Each product should have a non-empty name"
    
    # Verify product prices are displayed
    assert len(product_prices) > 0, "Product prices should be displayed"
    for price in product_prices:
        assert price is not None and price.strip() != "", "Each product should have a non-empty price"

@pytest.mark.products
@pytest.mark.sorting
@pytest.mark.positive
@pytest.mark.P1
def test_sort_products_by_name_a_to_z(driver, base_url):
    """Test that products can be sorted alphabetically from A to Z.
    
    Test ID: TC_PRODUCTS_002
    Steps:
        1. Login as standard_user
        2. Click sort dropdown
        3. Select Name (A to Z) option
        4. Verify products are sorted alphabetically A-Z
    
    Expected Results:
        - Products are displayed in alphabetical order from A to Z
    """
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Navigate to the login page
    driver.get(base_url)
    
    # Step 1: Login as standard_user
    login_page.login("standard_user", "secret_sauce")
    
    # Verify we're on the products page
    assert products_page.is_page_loaded(), "Products page should be loaded after login"
    
    # Step 2 & 3: Click sort dropdown and select Name (A to Z) option
    products_page.select_sort_option("az")
    
    # Step 4: Verify products are sorted alphabetically A-Z
    product_names = products_page.get_all_product_names()
    
    # Verify we have products to sort
    assert len(product_names) > 0, "There should be products displayed on the page"
    
    # Verify products are sorted alphabetically A-Z
    sorted_names = sorted(product_names, key=str.lower)
    assert product_names == sorted_names, f"Products should be sorted A-Z. Expected: {sorted_names}, Got: {product_names}"
    
    # Verify the active sort option shows the correct selection
    active_sort = products_page.get_active_sort_option()
    assert "A to Z" in active_sort or "az" in active_sort.lower(), f"Active sort option should indicate A to Z sorting, got: {active_sort}"