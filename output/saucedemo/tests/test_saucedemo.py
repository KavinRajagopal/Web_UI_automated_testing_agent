from pages.login_page import LoginPage
from pages.products_page import ProductsPage
import pytest

"""
Test ID: TC_LOGIN_001
Test Name: test_valid_login_with_standard_user
Description: Test valid login with standard_user credentials verifies successful authentication and redirect
"""


@pytest.mark.smoke
@pytest.mark.login
@pytest.mark.positive
@pytest.mark.P0
def test_valid_login_with_standard_user(driver, base_url):
    """
    Test valid login with standard_user credentials.
    
    This test verifies that a user can successfully log in with valid credentials
    and is redirected to the products page.
    
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
    login_page.login(username, password)
    
    # Step 5: Verify redirect to products page
    products_page = ProductsPage(driver)
    assert products_page.is_page_loaded(), "Products page failed to load after login"
    
    # Step 6: Verify URL contains /inventory.html
    current_url = driver.current_url
    assert "/inventory.html" in current_url, f"Expected URL to contain '/inventory.html', but got: {current_url}"
    
    # Step 7: Verify products title is displayed
    assert products_page.is_title_displayed(), "Products page title is not displayed"

"""
Test ID: TC_LOGIN_002
Test Name: test_invalid_login_with_wrong_password
Description: Test invalid login with wrong password displays appropriate error message
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_password(driver, base_url):
    """
    Test invalid login with wrong password displays appropriate error message.
    
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
    
    # Step 1: Navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify we're on the login page initially
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Enter standard_user username
    login_page.enter_username(username)
    
    # Step 3: Enter wrong_password
    login_page.enter_password(password)
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login"
    assert login_page.is_page_loaded(), "Login page should still be loaded"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Step 7: Verify error indicates invalid credentials
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    assert len(error_message) > 0, "Error message should not be empty"
    
    # Verify the error message indicates invalid credentials
    # Common error messages for invalid credentials contain keywords like:
    # "invalid", "incorrect", "wrong", "do not match", "username and password"
    error_lower = error_message.lower()
    invalid_credential_indicators = [
        "invalid",
        "incorrect", 
        "wrong",
        "do not match",
        "username and password",
        "credentials",
        "not match"
    ]
    
    has_invalid_indicator = any(indicator in error_lower for indicator in invalid_credential_indicators)
    assert has_invalid_indicator, f"Error message should indicate invalid credentials. Got: {error_message}"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_username(driver, base_url):
    """
    Test ID: TC_LOGIN_003
    Test Name: test_invalid_login_with_wrong_username
    Description: Test invalid login with wrong username displays appropriate error message
    
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
    
    # Navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Enter invalid username
    login_page.enter_username(username)
    
    # Enter valid password
    login_page.enter_password(password)
    
    # Click login button
    login_page.click_login()
    
    # Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login"
    
    # Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Verify error indicates invalid credentials
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    assert "username and password" in error_message.lower() or "invalid" in error_message.lower() or "do not match" in error_message.lower(), \
        f"Error message should indicate invalid credentials, got: {error_message}"

"""
Test ID: TC_LOGIN_004
Test Name: test_login_with_locked_out_user
Description: Test login with locked_out_user is prevented with appropriate error message
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P1
def test_login_with_locked_out_user(driver, base_url):
    """
    Test login with locked_out_user is prevented with appropriate error message.
    
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
    
    # Initialize login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify we are on the login page
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2 & 3 & 4: Enter credentials and click login
    login_page.login(username, password)
    
    # Step 5: Verify user remains on login page (login is prevented)
    assert login_page.is_on_page(), "User should remain on login page after failed login attempt"
    assert login_page.is_page_loaded(), "Login page should still be loaded"
    
    # Step 6: Verify error indicates user is locked out
    assert login_page.is_error_displayed(), "Error message should be displayed for locked out user"
    
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    assert "locked out" in error_message.lower(), \
        f"Error message should indicate user is locked out. Actual message: {error_message}"

"""
Test ID: TC_LOGIN_005
Test Name: test_login_with_empty_username
Description: Test login with empty username field shows validation error
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_username(driver, base_url):
    """
    Test that login with empty username field shows validation error.
    
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
    - Login is prevented
    """
    from selenium.webdriver.common.by import By
    
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify we're on the login page
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2 & 3: Leave username empty and enter password
    # We need to enter password only (username is left empty)
    password_field = driver.find_element(By.ID, "password")
    password_field.clear()
    password_field.send_keys("secret_sauce")
    
    # Step 4: Click login button
    login_button = driver.find_element(By.ID, "login-button")
    login_button.click()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login"
    assert login_page.is_page_loaded(), "Login page should still be loaded"
    
    # Step 6: Verify error indicates username is required
    assert login_page.is_error_displayed(), "Error message should be displayed"
    
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    assert "username is required" in error_message.lower(), \
        f"Error message should indicate username is required, got: {error_message}"

"""
Test ID: TC_LOGIN_006
Test Name: test_login_with_empty_password
Description: Test login with empty password field shows validation error
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_password(driver, base_url):
    """
    Test login with empty password field shows validation error.
    
    Steps:
    1. Navigate to login page
    2. Enter standard_user username
    3. Leave password field empty
    4. Click login button
    5. Verify user remains on login page
    6. Verify error indicates password is required
    
    Expected Results:
    - User remains on login page
    - Error message indicates password is required
    - Login is prevented
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify we're on the login page
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2: Enter standard_user username
    login_page.enter_username("standard_user")
    
    # Step 3: Leave password field empty (enter empty string)
    login_page.enter_password("")
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login"
    assert login_page.is_page_loaded(), "Login page should still be loaded"
    
    # Step 6: Verify error indicates password is required
    assert login_page.is_error_displayed(), "Error message should be displayed"
    
    error_message = login_page.get_error_message()
    assert "password" in error_message.lower() or "required" in error_message.lower(), \
        f"Error message should indicate password is required, got: {error_message}"
    
    # Verify login was prevented (still on login page with title visible)
    assert login_page.is_title_displayed(), "Login page title should still be displayed"

"""
Test ID: TC_LOGIN_007
Test Name: test_login_with_both_fields_empty
Description: Test login with both fields empty shows validation error
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P2
def test_login_with_both_fields_empty(driver, base_url):
    """
    Test login with both fields empty shows validation error.
    
    Steps:
    1. Navigate to login page
    2. Leave username field empty
    3. Leave password field empty
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    
    Expected Results:
    - User remains on login page
    - Error message is displayed
    - Login is prevented
    """
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Steps 2 & 3: Leave username and password fields empty
    # (Fields are empty by default, no action needed)
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after submitting empty fields"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed when both fields are empty"
    
    # Additional verification: Get error message to confirm it's related to validation
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"

"""
Test ID: TC_LOGIN_008
Test Name: test_login_with_special_characters_xss
Description: Test login with XSS special characters handles input safely
"""

from selenium.webdriver.remote.webdriver import WebDriver


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.edge_case
@pytest.mark.P2
def test_login_with_special_characters_xss(driver: WebDriver, base_url: str):
    """
    Test that login with XSS special characters handles input safely.
    
    This test verifies that:
    - User remains on login page after attempting XSS injection
    - Error message is displayed
    - No script execution occurs
    - Application handles malicious input safely
    """
    # Test data
    xss_username = "<script>alert(1)</script>"
    password = "secret_sauce"
    
    # Navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify we're on the login page
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Enter XSS script in username field
    login_page.enter_username(xss_username)
    
    # Enter password
    login_page.enter_password(password)
    
    # Click login button
    login_page.click_login()
    
    # Verify user remains on login page (login should fail)
    assert login_page.is_on_page(), "User should remain on login page after XSS attempt"
    
    # Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Get error message to verify it's a proper error response
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"
    
    # Verify no script execution occurs by checking page is still functional
    # If XSS executed, the page state would likely be corrupted
    assert login_page.is_page_loaded(), "Page should still be functional (no XSS execution)"
    assert login_page.is_title_displayed(), "Login title should still be displayed (no XSS corruption)"
    
    # Additional verification that the page title is intact (not modified by XSS)
    page_title = login_page.get_page_title()
    assert "script" not in page_title.lower(), "Page title should not contain script tags"

"""
Test ID: TC_PRODUCTS_001
Test Name: test_view_products_list_after_login
Description: Test viewing products list after successful login displays all product information
"""


@pytest.mark.products
@pytest.mark.positive
@pytest.mark.smoke
@pytest.mark.P0
def test_view_products_list_after_login(driver, base_url):
    """
    Test viewing products list after successful login displays all product information.
    
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
    # Test data
    username = "standard_user"
    password = "secret_sauce"
    
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Step 1: Navigate to login page and login with standard_user credentials
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Perform login
    login_page.login(username, password)
    
    # Step 2: Verify products page is displayed
    assert products_page.is_page_loaded(), "Products page should be loaded after login"
    assert products_page.is_on_page(), "Should be on products page"
    
    # Step 3: Verify title shows 'Products'
    assert products_page.is_title_displayed(), "Products page title should be displayed"
    title_text = products_page.get_title_text()
    assert title_text == "Products", f"Title should be 'Products', got '{title_text}'"
    
    # Step 4: Verify inventory container is visible
    assert products_page.is_element_visible("inventory_container"), "Inventory container should be visible"
    
    # Step 5: Verify inventory list contains products
    assert products_page.is_element_visible("inventory_list"), "Inventory list should be visible"
    
    # Step 6: Verify product names and prices are displayed
    # Get all products and verify they have names and prices
    products = products_page.get_all_products()
    assert len(products) > 0, "Should have at least one product displayed"
    
    # Verify each product has name and price
    for product in products:
        product_name = product.get("name", "")
        product_price = product.get("price", "")
        assert product_name, "Each product should have a name"
        assert product_price, "Each product should have a price"
    
    # Verify no error is displayed
    assert not products_page.is_error_displayed(), "No error should be displayed on products page"

"""
Test ID: TC_PRODUCTS_002
Test Name: test_sort_products_by_name_a_to_z
Description: Test sorting products by name A to Z orders products alphabetically
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@pytest.mark.products
@pytest.mark.sorting
@pytest.mark.positive
@pytest.mark.P1
def test_sort_products_by_name_a_to_z(driver, base_url):
    """
    Test sorting products by name A to Z orders products alphabetically.
    
    Steps:
    1. Login with standard_user credentials
    2. Click on product sort dropdown
    3. Select Name (A to Z) option
    4. Verify products are sorted alphabetically A-Z
    5. Verify active option shows correct selection
    
    Expected Results:
    - Products are sorted alphabetically from A to Z
    - First product starts with earlier letter
    - active-option shows 'Name (A to Z)'
    """
    # Initialize page objects
    login_page = LoginPage(driver)
    products_page = ProductsPage(driver)
    
    # Navigate to the login page
    driver.get(base_url)
    
    # Step 1: Login with standard_user credentials
    wait = WebDriverWait(driver, 10)
    
    # Wait for login page to load
    username_field = wait.until(
        EC.presence_of_element_located((By.ID, "user-name"))
    )
    username_field.send_keys("standard_user")
    
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys("secret_sauce")
    
    login_button = driver.find_element(By.ID, "login-button")
    login_button.click()
    
    # Wait for products page to load
    wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "inventory_list"))
    )
    
    # Verify we're on the products page
    assert products_page.is_page_loaded(), "Products page should be loaded after login"
    
    # Step 2: Click on product sort dropdown
    sort_dropdown = wait.until(
        EC.element_to_be_clickable((By.CLASS_NAME, "product_sort_container"))
    )
    sort_dropdown.click()
    
    # Step 3: Select Name (A to Z) option
    az_option = driver.find_element(By.CSS_SELECTOR, "option[value='az']")
    az_option.click()
    
    # Step 4: Verify products are sorted alphabetically A-Z
    # Get all product names
    product_name_elements = driver.find_elements(By.CLASS_NAME, "inventory_item_name")
    product_names = [element.text for element in product_name_elements]
    
    # Verify the list is sorted alphabetically
    sorted_names = sorted(product_names, key=str.lower)
    assert product_names == sorted_names, (
        f"Products should be sorted alphabetically A-Z. "
        f"Expected: {sorted_names}, Got: {product_names}"
    )
    
    # Verify first product starts with earlier letter than last product
    if len(product_names) > 1:
        first_product = product_names[0].lower()
        last_product = product_names[-1].lower()
        assert first_product <= last_product, (
            f"First product '{first_product}' should come before or equal to "
            f"last product '{last_product}' alphabetically"
        )
    
    # Step 5: Verify active option shows correct selection
    active_option = driver.find_element(By.CLASS_NAME, "active_option")
    active_option_text = active_option.text
    assert active_option_text == "Name (A to Z)", (
        f"Active option should show 'Name (A to Z)', but got '{active_option_text}'"
    )
    
    # Additional verification: Check dropdown value
    sort_dropdown_value = driver.find_element(
        By.CLASS_NAME, "product_sort_container"
    ).get_attribute("value")
    assert sort_dropdown_value == "az", (
        f"Sort dropdown value should be 'az', but got '{sort_dropdown_value}'"
    )