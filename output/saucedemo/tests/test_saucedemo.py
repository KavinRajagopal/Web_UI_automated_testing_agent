from pages.login_page import LoginPage
from pages.products_page import ProductsPage
import pytest
from selenium.webdriver.common.by import By

"""
Test ID: TC_LOGIN_001
Test Name: test_valid_login_with_standard_user
Description: Test valid login with standard_user credentials and verify successful redirect to products page
"""


@pytest.mark.smoke
@pytest.mark.login
@pytest.mark.positive
@pytest.mark.P0
def test_valid_login_with_standard_user(driver, base_url):
    """
    Test valid login with standard_user credentials and verify successful redirect to products page.
    
    Steps:
    1. Navigate to login page
    2. Enter standard_user username
    3. Enter secret_sauce password
    4. Click login button
    5. Verify redirect to products page
    6. Verify URL contains /inventory.html
    7. Verify products title is displayed
    
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
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Steps 2-4: Enter credentials and click login
    # Using the login method which handles entering username, password and clicking login
    login_page.login(username, password)
    
    # Step 5: Verify redirect to products page
    products_page = ProductsPage(driver)
    assert products_page.is_page_loaded(), "Products page failed to load after login"
    
    # Step 6: Verify URL contains /inventory.html
    current_url = driver.current_url
    assert "/inventory.html" in current_url, f"Expected URL to contain '/inventory.html', but got: {current_url}"
    
    # Step 7: Verify products title is displayed
    assert products_page.is_title_displayed(), "Products page title is not displayed"
    
    # Additional verification - check we're on the correct page
    assert products_page.is_on_page(), "Not on the products page as expected"

"""
Test ID: TC_LOGIN_002
Test Name: test_invalid_login_with_wrong_password
Description: Test login failure with correct username but incorrect password
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_password(driver, base_url):
    """
    Test login failure with correct username but incorrect password.
    
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
    
    # Initialize page object
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Step 2-4: Enter credentials and click login
    # Using the login method which handles entering username, password and clicking login
    login_page.login(username, password)
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Step 7: Verify error indicates invalid credentials
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    
    # Check that error message indicates invalid credentials
    # Common error messages for invalid credentials
    invalid_credential_indicators = [
        "username and password do not match",
        "invalid",
        "incorrect",
        "wrong",
        "not match",
        "Epic sadface"
    ]
    
    error_message_lower = error_message.lower()
    has_invalid_indicator = any(
        indicator.lower() in error_message_lower 
        for indicator in invalid_credential_indicators
    )
    
    assert has_invalid_indicator, (
        f"Error message should indicate invalid credentials. "
        f"Actual message: '{error_message}'"
    )


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_username(driver, base_url):
    """
    TC_LOGIN_003: Test login failure with incorrect username but correct password
    
    This test verifies that:
    - User remains on login page after invalid login attempt
    - Error message is displayed
    - Error indicates invalid credentials
    """
    # Initialize page object
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Step 2: Enter invalid username
    login_page.enter_username("invalid_user")
    
    # Step 3: Enter correct password
    login_page.enter_password("secret_sauce")
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Step 7: Verify error indicates invalid credentials
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    assert len(error_message) > 0, "Error message should not be empty"
    # Common error messages for invalid credentials
    assert any(keyword in error_message.lower() for keyword in ["username", "password", "not match", "invalid", "error"]), \
        f"Error message should indicate invalid credentials, got: {error_message}"

"""
Test ID: TC_LOGIN_004
Test Name: test_login_with_locked_out_user
Description: Test that locked_out_user account cannot login and receives appropriate error message
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P1
def test_login_with_locked_out_user(driver, base_url):
    """
    Test that locked_out_user account cannot login and receives appropriate error message.
    
    Steps:
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
    
    # Navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Enter locked_out_user username and password, then attempt login
    login_page.login(username, password)
    
    # Verify user remains on login page (login is prevented)
    assert login_page.is_on_page(), "User should remain on login page after failed login attempt"
    
    # Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for locked out user"
    
    # Verify error message indicates user is locked out
    error_message = login_page.get_error_message()
    assert "locked out" in error_message.lower(), \
        f"Error message should indicate user is locked out. Actual message: {error_message}"
    
    # Additional verification that login was prevented - page title should still be login page
    assert login_page.is_title_displayed(), "Login page title should still be displayed"

"""
Test ID: TC_LOGIN_005
Test Name: test_login_with_empty_username
Description: Test login validation when username field is empty
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_username(driver, base_url):
    """
    Test login validation when username field is empty.
    
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
    driver.get(base_url)
    
    # Verify we're on the login page
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2 & 3: Leave username empty, enter password, and click login
    # The login method will handle entering empty username and password
    login_page.login("", "secret_sauce")
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login attempt"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed"
    
    # Verify error message indicates username is required
    error_message = login_page.get_error_message()
    assert "username is required" in error_message.lower(), \
        f"Error message should indicate username is required, got: {error_message}"
    
    # Step 7: Verify login is prevented (user is still on login page)
    # This is confirmed by checking we're still on the login page
    assert login_page.is_title_displayed(), "Login page title should still be displayed"
    assert login_page.is_page_loaded(), "Login page should still be loaded, confirming login was prevented"

"""
Test ID: TC_LOGIN_006
Test Name: test_login_with_empty_password
Description: Test login validation when password field is empty
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_password(driver, base_url):
    """
    Test login validation when password field is empty.
    
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
    
    # Navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Enter username only (leave password empty)
    login_page.enter_username(username)
    login_page.enter_password(password)
    
    # Click login button
    login_page.click_login()
    
    # Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login"
    
    # Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed"
    
    # Verify error message indicates password is required
    error_message = login_page.get_error_message()
    assert "password" in error_message.lower() or "required" in error_message.lower(), \
        f"Error message should indicate password is required, got: {error_message}"
    
    # Verify login is prevented (user is still on login page)
    assert login_page.is_title_displayed(), "Login title should still be displayed indicating login was prevented"

"""
Test ID: TC_LOGIN_007
Test Name: test_login_with_both_fields_empty
Description: Test login validation when both username and password fields are empty
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P2
def test_login_with_both_fields_empty(driver, base_url):
    """
    Test login validation when both username and password fields are empty.
    
    Steps:
    1. Navigate to login page
    2. Leave username field empty
    3. Leave password field empty
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    7. Verify login is prevented
    
    Expected Results:
    - User remains on login page
    - Error message is displayed
    - Login is prevented
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Steps 2-3: Leave username and password fields empty (no input needed)
    # The fields are empty by default, so we proceed directly to clicking login
    
    # Step 4: Click login button
    # Since we need to trigger the login with empty fields, we use the page's login method
    # But first, let's verify we're on the login page
    assert login_page.is_on_page(), "Should be on login page before attempting login"
    
    # Attempt login with empty credentials
    login_page.login("", "")
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login attempt"
    assert login_page.is_page_loaded(), "Login page should still be loaded"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for empty credentials"
    
    # Get the error message for additional verification
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"
    
    # Step 7: Verify login is prevented (user is still on login page)
    # This is confirmed by the fact that we're still on the login page
    assert login_page.is_title_displayed(), "Login page title should still be displayed"
    
    # Additional verification that login was prevented
    current_url = driver.current_url
    assert "login" in current_url.lower() or base_url in current_url, \
        "URL should indicate user is still on login page, login was prevented"

"""
Test ID: TC_LOGIN_008
Test Name: test_login_with_special_characters_in_username
Description: Test XSS prevention by entering script tags in username field
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.edge_case
@pytest.mark.P2
def test_login_with_special_characters_in_username(driver, base_url):
    """
    Test XSS prevention by entering script tags in username field.
    
    This test verifies that the application properly handles and sanitizes
    potentially malicious input (XSS script tags) in the username field,
    preventing script execution and maintaining security.
    
    Steps:
    1. Navigate to login page
    2. Enter XSS script in username field
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    7. Verify no script execution occurs
    8. Verify application handles input safely
    
    Expected Results:
    - User remains on login page
    - Error message is displayed
    - No script execution occurs
    - Application handles input safely
    """
    # Test data
    xss_username = "<script>alert(1)</script>"
    password = "secret_sauce"
    
    # Step 1: Navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Enter XSS script in username field
    login_page.enter_username(xss_username)
    
    # Step 3: Enter secret_sauce password
    login_page.enter_password(password)
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after XSS attempt"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid username"
    
    # Step 7 & 8: Verify no script execution occurs and application handles input safely
    # If we reach this point without any JavaScript alert interrupting the test,
    # it means no script execution occurred
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should be present"
    assert len(error_message) > 0, "Error message should not be empty"
    
    # Additional verification that page is still functional (no script execution broke it)
    assert login_page.is_page_loaded(), "Page should still be functional after XSS attempt"
    assert login_page.is_title_displayed(), "Login title should still be displayed"
    
    # Verify the page title is still correct (application is handling input safely)
    page_title = login_page.get_page_title()
    assert "Swag Labs" in page_title, "Page title should indicate we're still on the login page"

"""
Test ID: TC_PRODUCTS_001
Test Name: test_view_products_list_after_login
Description: Test that products list is displayed correctly after successful login
"""


@pytest.mark.products
@pytest.mark.positive
@pytest.mark.smoke
@pytest.mark.P0
def test_view_products_list_after_login(driver, base_url):
    """
    Test that products list is displayed correctly after successful login.
    
    Steps:
    1. Login with standard_user credentials
    2. Verify products page is displayed
    3. Verify inventory container is visible
    4. Verify inventory list contains products
    5. Verify title shows Products
    6. Verify product names and prices are displayed
    
    Expected Results:
    - Products page is displayed
    - Title shows 'Products'
    - Multiple inventory items are visible
    - Product names and prices are displayed
    """
    # Test data
    username = "standard_user"
    password = "secret_sauce"
    
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Navigate to login page
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Login with standard_user credentials
    login_page.login(username, password)
    
    # Verify products page is displayed
    assert products_page.is_page_loaded(), "Products page should be displayed after login"
    assert products_page.is_on_page(), "Should be on products page"
    
    # Verify inventory container is visible
    assert products_page.is_element_visible(By.CSS_SELECTOR, "[data-test='inventory-container']"), "Inventory container should be visible"
    
    # Verify title shows 'Products'
    assert products_page.is_title_displayed(), "Products title should be displayed"
    title_text = products_page.get_title_text()
    assert title_text == "Products", f"Title should be 'Products', but got '{title_text}'"
    
    # Verify inventory list contains products
    assert products_page.is_element_visible(By.CSS_SELECTOR, "[data-test='inventory-list']"), "Inventory list should be visible"
    
    # Get all product items and verify there are multiple
    product_items = products_page.get_all_product_items()
    assert len(product_items) > 0, "There should be at least one product in the inventory"
    
    # Verify product names and prices are displayed
    product_names = products_page.get_all_product_names()
    product_prices = products_page.get_all_product_prices()
    
    assert len(product_names) > 0, "Product names should be displayed"
    assert len(product_prices) > 0, "Product prices should be displayed"
    assert len(product_names) == len(product_prices), "Each product should have a name and price"
    
    # Verify each product has a non-empty name and valid price
    for name in product_names:
        assert name and len(name.strip()) > 0, "Product name should not be empty"
    
    for price in product_prices:
        assert price and "$" in price, f"Product price should contain '$', but got '{price}'"

"""
Test ID: TC_PRODUCTS_002
Test Name: test_sort_products_by_name_a_to_z
Description: Test product sorting functionality by name in ascending alphabetical order
"""


@pytest.mark.products
@pytest.mark.sorting
@pytest.mark.positive
@pytest.mark.P1
def test_sort_products_by_name_a_to_z(driver, base_url):
    """
    Test product sorting functionality by name in ascending alphabetical order.
    
    Steps:
    1. Login with standard_user credentials
    2. Click on product sort dropdown
    3. Select Name (A to Z) option
    4. Verify products are sorted alphabetically A-Z
    5. Verify active option shows Name (A to Z)
    
    Expected Results:
    - Products are sorted alphabetically from A to Z
    - First product starts with earlier letter
    - active-option shows 'Name (A to Z)'
    """
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Navigate to the application
    driver.get(base_url)
    
    # Step 1: Login with standard_user credentials
    assert login_page.is_page_loaded(), "Login page should be loaded"
    login_page.login("standard_user", "secret_sauce")
    
    # Verify we're on the products page after login
    assert products_page.is_page_loaded(), "Products page should be loaded after login"
    assert products_page.is_title_displayed(), "Products title should be displayed"
    
    # Step 2 & 3: Click on product sort dropdown and select Name (A to Z)
    products_page.select_sort_option("az")
    
    # Step 4: Verify products are sorted alphabetically A-Z
    product_names = products_page.get_all_product_names()
    assert len(product_names) > 0, "There should be products displayed"
    
    # Verify the products are sorted alphabetically (A to Z)
    sorted_names = sorted(product_names, key=str.lower)
    assert product_names == sorted_names, (
        f"Products should be sorted alphabetically A-Z. "
        f"Expected: {sorted_names}, Got: {product_names}"
    )
    
    # Verify first product starts with an earlier letter in the alphabet
    if len(product_names) > 1:
        first_product = product_names[0].lower()
        last_product = product_names[-1].lower()
        assert first_product <= last_product, (
            f"First product '{first_product}' should come before or equal to "
            f"last product '{last_product}' alphabetically"
        )
    
    # Step 5: Verify active option shows Name (A to Z)
    active_sort_option = products_page.get_active_sort_option()
    assert active_sort_option == "Name (A to Z)", (
        f"Active sort option should be 'Name (A to Z)', but got '{active_sort_option}'"
    )