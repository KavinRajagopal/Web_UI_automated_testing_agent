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
        2. Enter standard_user username
        3. Enter secret_sauce password
        4. Click login button
        5. Verify redirect to products page
        6. Verify URL contains /inventory.html
        7. Verify Products title is displayed
    
    Expected Results:
        - User is redirected to products page
        - URL contains '/inventory.html'
        - Products title is displayed
    """
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Enter standard_user username
    login_page.enter_username("standard_user")
    
    # Step 3: Enter secret_sauce password
    login_page.enter_password("secret_sauce")
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify redirect to products page
    assert products_page.is_page_loaded(), "Products page should be loaded after successful login"
    
    # Step 6: Verify URL contains /inventory.html
    current_url = driver.current_url
    assert "/inventory.html" in current_url, f"URL should contain '/inventory.html', but got: {current_url}"
    
    # Step 7: Verify Products title is displayed
    assert products_page.is_products_page_displayed(), "Products page title should be displayed"

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
    3. Enter wrong_password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    7. Verify error indicates invalid credentials
    
    Expected Results:
    - User remains on login page
    - Error message is displayed
    - Error indicates invalid credentials
    """
    # Test data
    username = "standard_user"
    password = "wrong_password"
    
    # Initialize LoginPage and navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Enter standard_user username
    login_page.enter_username(username)
    
    # Enter wrong password
    login_page.enter_password(password)
    
    # Click login button
    login_page.click_login_button()
    
    # Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Verify error indicates invalid credentials
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
    Description: Test login failure with wrong username but correct password
    
    Steps:
    1. Navigate to login page
    2. Enter invalid_user username
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    7. Verify error indicates invalid credentials
    
    Expected Results: Test passes - login should fail with error message
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Enter invalid username
    login_page.enter_username("invalid_user")
    
    # Step 3: Enter correct password
    login_page.enter_password("secret_sauce")
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Step 7: Verify error indicates invalid credentials
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    assert "username" in error_message.lower() or "password" in error_message.lower() or "match" in error_message.lower() or "invalid" in error_message.lower(), \
        f"Error message should indicate invalid credentials, got: {error_message}"

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
    2. Enter locked_out_user username
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error indicates user is locked out
    
    Expected Results:
    - User remains on login page
    - Error message indicates user is locked out
    - Login is prevented
    """
    # Test data
    username = "locked_out_user"
    password = "secret_sauce"
    
    # Initialize LoginPage and navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Enter locked_out_user username
    login_page.enter_username(username)
    
    # Enter secret_sauce password
    login_page.enter_password(password)
    
    # Click login button
    login_page.click_login_button()
    
    # Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Verify error is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for locked out user"
    
    # Verify error message indicates user is locked out
    error_message = login_page.get_error_message()
    assert "locked out" in error_message.lower(), f"Error message should indicate user is locked out, got: {error_message}"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_username(driver, base_url):
    """
    Test ID: TC_LOGIN_005
    Test Name: test_login_with_empty_username
    Description: Test login validation when username field is empty
    
    Steps:
    1. Navigate to login page
    2. Leave username field empty
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error indicates username is required
    
    Expected Results:
    - User remains on login page
    - Error message indicates username is required
    """
    # Initialize LoginPage
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Leave username field empty (clear it to ensure it's empty)
    login_page.clear_username()
    
    # Step 3: Enter password
    login_page.enter_password("secret_sauce")
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error is displayed and indicates username is required
    assert login_page.is_error_displayed(), "Error message should be displayed"
    error_message = login_page.get_error_message()
    assert "username is required" in error_message.lower(), f"Error should indicate username is required, got: {error_message}"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_password(driver, base_url):
    """
    Test ID: TC_LOGIN_006
    Test Name: test_login_with_empty_password
    Description: Test login validation when password field is empty
    
    Steps:
    1. Navigate to login page
    2. Enter standard_user username
    3. Leave password field empty
    4. Click login button
    5. Verify user remains on login page
    6. Verify error indicates password is required
    
    Expected Results: Test passes with appropriate error message
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Enter standard_user username
    login_page.enter_username("standard_user")
    
    # Step 3: Leave password field empty (explicitly clear it to ensure it's empty)
    login_page.clear_password()
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error indicates password is required
    assert login_page.is_error_displayed(), "Error message should be displayed"
    error_message = login_page.get_error_message()
    assert "password" in error_message.lower() or "required" in error_message.lower(), \
        f"Error message should indicate password is required, got: {error_message}"

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
    2. Leave username field empty
    3. Leave password field empty
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    
    Expected Results: Test passes - error message displayed and user remains on login page
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Step 2 & 3: Leave username and password fields empty (clear them to ensure they're empty)
    login_page.clear_username()
    login_page.clear_password()
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after submitting empty fields"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed when both fields are empty"

@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.edge_case
@pytest.mark.P2
def test_login_with_special_characters_in_username(driver, base_url):
    """
    TC_LOGIN_008: Test that application safely handles special characters and XSS attempts in username field.
    
    Steps:
    1. Navigate to login page
    2. Enter XSS script in username field
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    7. Verify no script execution occurs
    
    Expected Results:
    - Application safely handles XSS attempt
    - User remains on login page
    - Error message is displayed
    - No script execution occurs
    """
    # Initialize login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Enter XSS script in username field
    xss_payload = "<script>alert('XSS')</script>"
    login_page.enter_username(xss_payload)
    
    # Step 3: Enter secret_sauce password
    login_page.enter_password("secret_sauce")
    
    # Step 4: Click login button
    login_page.click_login_button()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after XSS attempt"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed"
    
    # Get error message to verify it's a proper error response
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"
    
    # Step 7: Verify no script execution occurs (page should still be functional)
    # If XSS executed, the page structure would likely be compromised
    assert login_page.is_page_loaded(), "Page should still be functional after XSS attempt (no script execution)"
    
    # Additional security check: Verify the page title hasn't been modified by script
    current_url = driver.current_url
    assert "javascript:" not in current_url.lower(), "URL should not contain javascript protocol"

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
    1. Login with standard_user credentials
    2. Verify products page is displayed
    3. Verify inventory container is visible
    4. Verify inventory list contains products
    5. Verify product names and prices are displayed
    
    Expected Results:
    - Products page is displayed
    - Title shows 'Products'
    - Multiple inventory items are visible
    - Product names and prices are displayed
    """
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Navigate to login page
    driver.get(base_url)
    
    # Step 1: Login with standard_user credentials
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
    
    # Step 4: Verify inventory list contains products
    product_count = products_page.get_product_count()
    assert product_count > 0, f"Should have at least one product, but got {product_count}"
    
    # Step 5: Verify product names and prices are displayed
    product_names = products_page.get_all_product_names()
    assert len(product_names) > 0, "Product names should be displayed"
    assert all(name for name in product_names), "All product names should be non-empty"
    
    product_prices = products_page.get_all_product_prices()
    assert len(product_prices) > 0, "Product prices should be displayed"
    # Parse price strings (e.g., "$29.99") to floats before comparing
    numeric_prices = [float(price.replace('$', '')) for price in product_prices]
    assert all(price > 0 for price in numeric_prices), "All product prices should be greater than 0"
    
    # Verify counts match
    assert len(product_names) == len(product_prices), "Number of product names should match number of prices"

@pytest.mark.products
@pytest.mark.sorting
@pytest.mark.positive
@pytest.mark.P1
def test_sort_products_by_name_a_to_z(driver, base_url):
    """Test that products can be sorted alphabetically from A to Z.
    
    Test ID: TC_PRODUCTS_002
    
    Steps:
    1. Login with standard_user credentials
    2. Click on product sort dropdown
    3. Select Name (A to Z) option
    4. Verify products are sorted alphabetically A-Z
    5. Verify active option shows correct selection
    
    Expected Results:
    - Products are sorted alphabetically from A to Z
    - Active sort option displays 'Name (A to Z)'
    """
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Navigate to the application
    driver.get(base_url)
    
    # Step 1: Login with standard_user credentials
    login_page.login("standard_user", "secret_sauce")
    
    # Verify we are on the products page
    assert products_page.is_page_loaded(), "Products page should be loaded after login"
    
    # Step 2 & 3: Click on product sort dropdown and select Name (A to Z) option
    products_page.select_sort_option("az")
    
    # Step 4: Verify products are sorted alphabetically A-Z
    assert products_page.are_products_sorted_az(), "Products should be sorted alphabetically from A to Z"
    
    # Step 5: Verify active option shows correct selection
    active_option = products_page.get_active_sort_option()
    assert "Name (A to Z)" in active_option, f"Active sort option should show 'Name (A to Z)', but got '{active_option}'"