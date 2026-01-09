from pages.login_page import LoginPage
from pages.products_page import ProductsPage
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


@pytest.mark.smoke
@pytest.mark.login
@pytest.mark.positive
@pytest.mark.P0
def test_valid_login_with_standard_user(driver, base_url):
    """
    Test ID: TC_LOGIN_001
    Test Name: test_valid_login_with_standard_user
    Description: Test valid login with standard_user credentials verifies successful authentication
    
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
    # Test data
    username = "standard_user"
    password = "secret_sauce"
    
    # Step 1: Navigate to login page
    login_page = LoginPage(driver)
    login_page.navigate(base_url)
    
    # Step 2: Enter standard_user username
    login_page.enter_username(username)
    
    # Step 3: Enter secret_sauce password
    login_page.enter_password(password)
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5-7: Verify redirect to products page and assertions
    products_page = ProductsPage(driver)
    
    # Verify URL contains /inventory.html
    current_url = driver.current_url
    assert "/inventory.html" in current_url, f"Expected URL to contain '/inventory.html', but got '{current_url}'"
    
    # Verify Products title is displayed
    assert products_page.is_page_loaded(), "Products title is not displayed after login"
    
    # Additional verification - check the title text
    title_text = products_page.get_page_title()
    assert title_text == "Products", f"Expected title 'Products', but got '{title_text}'"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_password(driver, base_url):
    """
    Test ID: TC_LOGIN_002
    Test Name: test_invalid_login_with_wrong_password
    Description: Test login fails with correct username but wrong password
    
    This test verifies that:
    - User remains on login page after failed login attempt
    - Error message is displayed
    - Error indicates invalid credentials
    
    Test Data:
        username: standard_user
        password: wrong_password
    
    Expected Results:
        - User remains on login page
        - Error message is displayed
        - Error indicates invalid credentials
    """
    # Test data
    username = "standard_user"
    password = "wrong_password"
    
    # Initialize page object
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    login_page.navigate(base_url)
    
    # Step 2: Enter standard_user username
    login_page.enter_username(username)
    
    # Step 3: Enter wrong_password
    login_page.enter_password(password)
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed"
    
    # Step 7: Verify error indicates invalid credentials
    error_text = login_page.get_error_message()
    assert error_text is not None, "Error message text should not be None"
    
    # The error message should indicate invalid credentials
    expected_error_keywords = ["username", "password", "do not match"]
    error_text_lower = error_text.lower()
    
    assert any(keyword in error_text_lower for keyword in expected_error_keywords), \
        f"Error message should indicate invalid credentials. Got: {error_text}"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_username(driver, base_url):
    """
    Test login fails with invalid username and correct password.
    
    Test ID: TC_LOGIN_003
    
    Steps:
        1. Navigate to login page
        2. Enter invalid_user username
        3. Enter secret_sauce password
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
    username = "invalid_user"
    password = "secret_sauce"
    
    # Step 1: Navigate to login page
    login_page = LoginPage(driver)
    login_page.navigate(base_url)
    
    # Step 2: Enter invalid_user username
    login_page.enter_username(username)
    
    # Step 3: Enter secret_sauce password
    login_page.enter_password(password)
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Step 7: Verify error indicates invalid credentials
    error_message = login_page.get_error_message()
    assert "Username and password do not match" in error_message or \
           "invalid" in error_message.lower() or \
           "not match" in error_message.lower(), \
           f"Error message should indicate invalid credentials, got: {error_message}"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P1
def test_login_locked_out_user_should_fail(driver, base_url):
    """
    Test ID: TC_LOGIN_004
    Test Name: test_login_locked_out_user_should_fail
    Description: Test locked out user cannot login even with correct credentials
    
    This test verifies that a locked out user is prevented from logging in
    even when providing correct credentials. The system should display an
    appropriate error message indicating the account is locked.
    
    Test Steps:
    1. Navigate to login page
    2. Enter locked_out_user username
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message indicates user is locked out
    7. Verify login is prevented
    
    Expected Results:
    - User remains on login page
    - Error message indicates user is locked out
    - Login is prevented
    """
    # Test data
    username = "locked_out_user"
    password = "secret_sauce"
    
    # Initialize page object
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    login_page.navigate(base_url)
    
    # Verify we're on the login page
    assert login_page.is_on_login_page(), "Failed to navigate to login page"
    
    # Step 2: Enter locked_out_user username
    login_page.enter_username(username)
    
    # Step 3: Enter secret_sauce password
    login_page.enter_password(password)
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message indicates user is locked out
    assert login_page.is_error_displayed(), "Error message should be displayed"
    error_text = login_page.get_error_message()
    assert "locked out" in error_text.lower(), f"Error message should indicate user is locked out. Got: {error_text}"
    
    # Step 7: Verify login is prevented (URL should still be login page)
    current_url = driver.current_url
    assert "inventory" not in current_url, "User should not be redirected to inventory page"
    assert base_url in current_url, f"User should remain on login page. Current URL: {current_url}"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_username(driver, base_url):
    """
    Test ID: TC_LOGIN_005
    Test Name: test_login_with_empty_username
    Description: Test that login validation requires username field.
    
    Steps:
    1. Navigate to login page
    2. Leave username field empty
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message indicates username is required
    7. Verify login is prevented
    
    Expected Results:
    - User remains on login page
    - Error message indicates username is required
    - Login is prevented
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    login_page.navigate(base_url)
    
    # Step 2 & 3: Leave username empty and enter password
    # Step 4: Click login button
    login_page.login("", "secret_sauce")
    
    # Step 5: Verify user remains on login page
    current_url = driver.current_url
    assert base_url in current_url or "inventory" not in current_url, \
        "User should remain on login page but was redirected"
    
    # Step 6: Verify error message indicates username is required
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should be displayed"
    assert "username is required" in error_message.lower(), \
        f"Error message should indicate username is required, got: {error_message}"
    
    # Step 7: Verify login is prevented (user is still on login page)
    assert "inventory" not in driver.current_url.lower(), \
        "Login should be prevented - user should not reach inventory page"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_password(driver, base_url):
    """
    Test ID: TC_LOGIN_006
    Test Name: test_login_with_empty_password
    Description: Test login validation requires password field
    
    Steps:
    1. Navigate to login page
    2. Enter standard_user username
    3. Leave password field empty
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message indicates password is required
    7. Verify login is prevented
    
    Expected Results:
    - User remains on login page
    - Error message indicates password is required
    - Login is prevented
    """
    # Test data
    username = "standard_user"
    password = ""
    
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    login_page.navigate(base_url)
    
    # Verify we're on the login page initially
    assert login_page.is_on_login_page(), "Should be on login page initially"
    
    # Step 2: Enter standard_user username
    login_page.enter_username(username)
    
    # Step 3: Leave password field empty (enter empty string)
    login_page.enter_password(password)
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), "User should remain on login page after failed login attempt"
    
    # Step 6: Verify error message indicates password is required
    assert login_page.is_error_displayed(), "Error message should be displayed"
    error_message = login_page.get_error_message()
    assert "password is required" in error_message.lower(), \
        f"Error message should indicate password is required, got: {error_message}"
    
    # Step 7: Verify login is prevented (user is still on login page, not redirected)
    current_url = driver.current_url
    assert "inventory" not in current_url.lower(), \
        "User should not be redirected to inventory page - login should be prevented"
    assert login_page.is_on_login_page(), "Login should be prevented - user should still be on login page"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P2
def test_login_with_both_fields_empty(driver, base_url):
    """
    Test ID: TC_LOGIN_007
    Test Name: test_login_with_both_fields_empty
    Description: Test login validation when both username and password fields are empty.
    
    This test verifies that:
    1. User remains on the login page after attempting login with empty fields
    2. An appropriate error message is displayed
    3. Login is prevented when both fields are empty
    
    Test Data:
        username: (empty)
        password: (empty)
    
    Expected Results:
        - User remains on login page
        - Error message is displayed
        - Login is prevented
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    login_page.navigate(base_url)
    
    # Step 2: Leave username field empty
    login_page.enter_username("")
    
    # Step 3: Leave password field empty
    login_page.enter_password("")
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_login_page(), \
        f"User should remain on login page, but current URL is: {driver.current_url}"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed"
    
    # Get the error message text
    error_text = login_page.get_error_message()
    assert error_text is not None and len(error_text) > 0, \
        "Error message should contain text"
    
    # Step 7: Verify login is prevented
    current_url = driver.current_url
    assert "inventory" not in current_url, \
        "Login should be prevented - no redirect to inventory page"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.edge_case
@pytest.mark.P2
def test_login_with_special_characters_in_username(driver, base_url):
    """
    Test ID: TC_LOGIN_008
    Test Name: test_login_with_special_characters_in_username
    Description: Test XSS prevention in username field with script injection attempt
    
    This test verifies that:
    - User remains on login page after XSS injection attempt
    - Error message is displayed
    - No script execution occurs
    - Application handles input safely
    
    Steps:
    1. Navigate to login page
    2. Enter XSS script in username field
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    7. Verify no script execution occurs
    8. Verify application handles input safely
    """
    # Test data
    xss_username = "<script>alert(1)</script>"
    password = "secret_sauce"
    
    # Step 1: Navigate to login page
    login_page = LoginPage(driver)
    login_page.navigate(base_url)
    
    # Step 2: Enter XSS script in username field
    login_page.enter_username(xss_username)
    
    # Step 3: Enter secret_sauce password
    login_page.enter_password(password)
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    current_url = driver.current_url
    assert base_url in current_url, f"User should remain on login page, but URL is: {current_url}"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid username"
    
    error_message = login_page.get_error_message()
    assert error_message, "Error message text should not be empty"
    
    # Step 7: Verify no script execution occurs
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        alert.dismiss()
        pytest.fail(f"XSS vulnerability detected! Alert was triggered with text: {alert_text}")
    except Exception:
        pass
    
    # Step 8: Verify application handles input safely
    page_source = driver.page_source
    assert "<script>alert(1)</script>" not in page_source.lower() or \
           "&lt;script&gt;" in page_source.lower() or \
           "error" in page_source.lower(), \
           "XSS script should be handled safely (escaped or rejected)"


@pytest.mark.products
@pytest.mark.positive
@pytest.mark.smoke
@pytest.mark.P0
def test_view_products_list_after_login(driver, base_url):
    """
    TC_PRODUCTS_001: Test products page displays correctly after successful login
    
    This test verifies that after a successful login with standard_user credentials,
    the products page is displayed correctly with all expected elements:
    - Products page is displayed
    - Title shows 'Products'
    - Multiple inventory items are visible
    - Product names and prices are displayed
    """
    # Test Data
    username = "standard_user"
    password = "secret_sauce"
    
    # Step 1: Navigate to login page and login with standard_user credentials
    login_page = LoginPage(driver)
    login_page.navigate(base_url)
    login_page.login(username, password)
    
    # Step 2: Initialize products page and verify products page is displayed
    products_page = ProductsPage(driver)
    assert products_page.is_page_loaded(), "Products page is not displayed after login"
    
    # Step 3: Verify inventory container is visible
    assert products_page.is_inventory_container_visible(), "Inventory container is not visible"
    
    # Step 4: Verify inventory list contains products
    inventory_items = products_page.get_inventory_items()
    assert len(inventory_items) > 0, "No inventory items found on the products page"
    
    # Step 5: Verify title shows 'Products'
    page_title = products_page.get_page_title()
    assert page_title == "Products", f"Expected title 'Products', but got '{page_title}'"
    
    # Step 6: Verify product names and prices are displayed
    product_names = products_page.get_product_names()
    product_prices = products_page.get_product_prices()
    
    # Verify we have product names
    assert len(product_names) > 0, "No product names found"
    for name in product_names:
        assert name.strip() != "", "Found empty product name"
    
    # Verify we have product prices
    assert len(product_prices) > 0, "No product prices found"
    for price in product_prices:
        assert price.strip() != "", "Found empty product price"
        assert "$" in price, f"Price '{price}' does not contain dollar sign"
    
    # Verify counts match
    assert len(product_names) == len(product_prices), \
        f"Mismatch between product names ({len(product_names)}) and prices ({len(product_prices)})"
    
    # Additional assertion: Verify multiple inventory items are visible (at least 2)
    assert len(inventory_items) >= 2, \
        f"Expected multiple inventory items, but found only {len(inventory_items)}"


@pytest.mark.products
@pytest.mark.sorting
@pytest.mark.positive
@pytest.mark.P1
def test_sort_products_by_name_a_to_z(driver, base_url):
    """
    Test ID: TC_PRODUCTS_002
    Test Name: test_sort_products_by_name_a_to_z
    Description: Test product sorting functionality by name ascending order
    
    Steps:
    1. Login with standard_user credentials
    2. Click on product sort dropdown
    3. Select Name (A to Z) option
    4. Verify products are sorted alphabetically A-Z
    5. Verify first product starts with earlier letter
    6. Verify active option shows Name (A to Z)
    
    Expected Results:
    - Products are sorted alphabetically from A to Z
    - First product starts with earlier letter
    - active-option shows 'Name (A to Z)'
    """
    # Test Data
    username = "standard_user"
    password = "secret_sauce"
    sort_option = "az"
    expected_sort_text = "Name (A to Z)"
    
    # Step 1: Navigate to login page and login with standard_user credentials
    login_page = LoginPage(driver)
    login_page.navigate(base_url)
    login_page.login(username, password)
    
    # Initialize products page
    products_page = ProductsPage(driver)
    
    # Verify we're on the products page
    assert products_page.is_page_loaded(), "Failed to navigate to products page after login"
    
    # Step 2 & 3: Select Name (A to Z) option from sort dropdown
    sort_dropdown = driver.find_element(By.CLASS_NAME, "product_sort_container")
    select = Select(sort_dropdown)
    select.select_by_value(sort_option)
    
    # Step 4: Verify products are sorted alphabetically A-Z
    product_names = products_page.get_product_names()
    assert len(product_names) > 0, "No products found on the page"
    
    sorted_names = sorted(product_names, key=str.lower)
    assert product_names == sorted_names, (
        f"Products are not sorted alphabetically A-Z. "
        f"Expected: {sorted_names}, Got: {product_names}"
    )
    
    # Step 5: Verify first product starts with earlier letter
    if len(product_names) > 1:
        first_product_first_char = product_names[0][0].lower()
        second_product_first_char = product_names[1][0].lower()
        assert first_product_first_char <= second_product_first_char, (
            f"First product '{product_names[0]}' does not start with an earlier or equal letter "
            f"compared to second product '{product_names[1]}'"
        )
    
    # Step 6: Verify active option shows Name (A to Z)
    sort_dropdown = driver.find_element(By.CLASS_NAME, "product_sort_container")
    select = Select(sort_dropdown)
    active_option = select.first_selected_option.text
    assert active_option == expected_sort_text, (
        f"Active sort option is incorrect. Expected: '{expected_sort_text}', Got: '{active_option}'"
    )