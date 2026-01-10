import pytest
from pages.login_page import LoginPage
from pages.products_page import ProductsPage


"""
Test ID: TC_LOGIN_001
Test Name: test_valid_login_with_standard_user
Description: Test valid login with standard_user credentials redirects to products page
"""


@pytest.mark.smoke
@pytest.mark.login
@pytest.mark.positive
@pytest.mark.P0
def test_valid_login_with_standard_user(driver, base_url):
    """
    Test valid login with standard_user credentials redirects to products page.
    
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
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Steps 2-4: Enter credentials and click login
    # Using the login method which handles entering username, password and clicking login
    login_page.login(username, password)
    
    # Step 5: Verify redirect to products page
    products_page = ProductsPage(driver)
    assert products_page.is_page_loaded(), "Products page should be loaded after successful login"
    
    # Step 6: Verify URL contains /inventory.html
    current_url = driver.current_url
    assert "/inventory.html" in current_url, f"URL should contain '/inventory.html', but got: {current_url}"
    
    # Step 7: Verify products title is displayed
    assert products_page.is_title_displayed(), "Products title should be displayed"


"""
Test ID: TC_LOGIN_002
Test Name: test_invalid_login_with_wrong_password
Description: Test login fails with wrong password and displays appropriate error
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_password(driver, base_url):
    """
    Test that login fails with wrong password and displays appropriate error message.
    
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
    login_page.navigate(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Step 2-4: Enter credentials and attempt login
    login_page.login(username, password)
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Step 7: Verify error indicates invalid credentials
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    
    # Check that error message contains relevant text about invalid credentials
    error_message_lower = error_message.lower()
    assert any(keyword in error_message_lower for keyword in ["username", "password", "match", "invalid", "incorrect", "wrong"]), \
        f"Error message should indicate invalid credentials. Got: {error_message}"


"""
Test ID: TC_LOGIN_003
Test Name: test_invalid_login_with_wrong_username
Description: Test login fails with wrong username and displays appropriate error
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P0
def test_invalid_login_with_wrong_username(driver, base_url):
    """
    Test that login fails with wrong username and displays appropriate error message.
    
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
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2-4: Enter invalid credentials and click login
    login_page.login(username, password)
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid credentials"
    
    # Step 7: Verify error indicates invalid credentials
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    
    # Check that error message contains relevant text about invalid credentials
    error_lower = error_message.lower()
    assert any(keyword in error_lower for keyword in ["username", "password", "not match", "invalid", "do not match"]), \
        f"Error message should indicate invalid credentials, got: {error_message}"


"""
Test ID: TC_LOGIN_004
Test Name: test_login_locked_out_user_fails
Description: Test locked_out_user cannot login and receives locked out error message
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.P1
def test_login_locked_out_user_fails(driver, base_url):
    """
    Test that a locked out user cannot login and receives an appropriate error message.
    
    Steps:
    1. Navigate to login page
    2. Enter locked_out_user username
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message indicates user is locked out
    
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
    
    # Enter locked_out_user credentials and attempt login
    login_page.login(username, password)
    
    # Verify user remains on login page (login was prevented)
    assert login_page.is_on_page(), "User should remain on login page after failed login attempt"
    
    # Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for locked out user"
    
    # Verify error message indicates user is locked out
    error_message = login_page.get_error_message()
    assert "locked out" in error_message.lower(), \
        f"Error message should indicate user is locked out. Actual message: {error_message}"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_username(driver, base_url):
    """
    TC_LOGIN_005: Test login fails with empty username field and shows validation error
    
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
    # Initialize the login page
    login_page = LoginPage(driver)
    
    # Step 1: Navigate to login page
    driver.get(base_url)
    
    # Verify we're on the login page
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Step 2 & 3: Leave username empty and enter password
    # We need to interact with the page directly since login method isn't available
    # Enter empty username (just clear the field) and enter password
    from selenium.webdriver.common.by import By
    username_field = driver.find_element(By.ID, "user-name")
    password_field = driver.find_element(By.ID, "password")
    login_button = driver.find_element(By.ID, "login-button")
    
    # Step 2: Leave username field empty (clear it to ensure it's empty)
    username_field.clear()
    
    # Step 3: Enter password
    password_field.clear()
    password_field.send_keys("secret_sauce")
    
    # Step 4: Click login button
    login_button.click()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login attempt"
    
    # Step 6: Verify error indicates username is required
    assert login_page.is_error_displayed(), "Error message should be displayed"
    
    error_message = login_page.get_error_message()
    assert "username is required" in error_message.lower(), \
        f"Error message should indicate username is required, but got: {error_message}"


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P1
def test_login_with_empty_password(driver, base_url):
    """
    Test ID: TC_LOGIN_006
    Test Name: test_login_with_empty_password
    Description: Test login fails with empty password field and shows validation error
    
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
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Step 2: Enter standard_user username
    login_page.enter_username("standard_user")
    
    # Step 3: Leave password field empty (enter empty string)
    login_page.enter_password("")
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login attempt"
    assert login_page.is_page_loaded(), "Login page should still be loaded"
    
    # Step 6: Verify error indicates password is required
    assert login_page.is_error_displayed(), "Error message should be displayed for empty password"
    
    error_message = login_page.get_error_message()
    assert error_message is not None, "Error message should not be None"
    assert "password" in error_message.lower() or "required" in error_message.lower(), \
        f"Error message should indicate password is required. Actual message: {error_message}"


"""
Test ID: TC_LOGIN_007
Test Name: test_login_with_both_fields_empty
Description: Test login fails with both fields empty and shows validation error
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.validation
@pytest.mark.boundary
@pytest.mark.P2
def test_login_with_both_fields_empty(driver, base_url):
    """
    Test that login fails when both username and password fields are empty.
    
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
    login_page.navigate(base_url)
    
    # Verify we are on the login page
    assert login_page.is_page_loaded(), "Login page failed to load"
    
    # Steps 2 & 3: Leave both fields empty (don't enter anything)
    # The fields should already be empty by default
    
    # Step 4: Click login button
    login_page.click_login()
    
    # Step 5: Verify user remains on login page
    assert login_page.is_on_page(), "User should remain on login page after failed login attempt"
    assert login_page.is_page_loaded(), "Login page should still be loaded"
    
    # Step 6: Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed when both fields are empty"
    
    # Additional verification: Get and log the error message
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"


"""
Test ID: TC_LOGIN_008
Test Name: test_login_with_special_characters_xss
Description: Test application handles XSS injection attempt safely in username field
"""


@pytest.mark.login
@pytest.mark.negative
@pytest.mark.security
@pytest.mark.edge_case
@pytest.mark.P2
def test_login_with_special_characters_xss(driver, base_url):
    """
    Test application handles XSS injection attempt safely in username field.
    
    Steps:
    1. Navigate to login page
    2. Enter XSS script in username field
    3. Enter secret_sauce password
    4. Click login button
    5. Verify user remains on login page
    6. Verify error message is displayed
    7. Verify no script execution occurs
    
    Expected Results:
    - User remains on login page
    - Error message is displayed
    - No script execution occurs
    - Application handles input safely
    """
    # Test data
    xss_username = "<script>alert(1)</script>"
    password = "secret_sauce"
    
    # Navigate to login page
    login_page = LoginPage(driver)
    driver.get(base_url)
    
    # Verify login page is loaded
    assert login_page.is_page_loaded(), "Login page should be loaded"
    
    # Enter XSS script in username field and password
    login_page.login(xss_username, password)
    
    # Verify user remains on login page (login should fail)
    assert login_page.is_on_page(), "User should remain on login page after XSS attempt"
    
    # Verify error message is displayed
    assert login_page.is_error_displayed(), "Error message should be displayed for invalid login"
    
    # Get error message to verify it's a proper error response
    error_message = login_page.get_error_message()
    assert error_message is not None and len(error_message) > 0, "Error message should not be empty"
    
    # Verify no script execution by checking page is still functional
    # If XSS executed, the page might be broken or show unexpected behavior
    assert login_page.is_title_displayed(), "Page title should still be displayed (no XSS disruption)"
    
    # Verify the login page elements are still present and visible
    # This confirms the application handled the malicious input safely
    assert login_page.is_page_loaded(), "Login page should still be fully functional after XSS attempt"


"""
Test ID: TC_PRODUCTS_001
Test Name: test_view_products_list_after_login
Description: Test products list is displayed correctly after successful login
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
    assert title_text == "Products", f"Title should be 'Products', but got '{title_text}'"
    
    # Step 4: Verify inventory container is visible
    assert products_page.is_inventory_container_visible(), "Inventory container should be visible"
    
    # Step 5: Verify inventory list contains products
    product_count = products_page.get_product_count()
    assert product_count > 0, f"Should have multiple inventory items, but got {product_count}"
    
    # Step 6: Verify product names and prices are displayed
    product_names = products_page.get_all_product_names()
    assert len(product_names) > 0, "Product names should be displayed"
    for name in product_names:
        assert name and len(name) > 0, "Each product should have a non-empty name"
    
    product_prices = products_page.get_all_product_prices()
    assert len(product_prices) > 0, "Product prices should be displayed"
    for price in product_prices:
        assert price and "$" in price, f"Each product should have a valid price, but got '{price}'"
    
    # Verify no errors are displayed
    assert not products_page.is_error_displayed(), "No errors should be displayed on products page"


"""
Test ID: TC_PRODUCTS_002
Test Name: test_sort_products_by_name_a_to_z
Description: Test products can be sorted alphabetically from A to Z
"""


@pytest.mark.products
@pytest.mark.sorting
@pytest.mark.positive
@pytest.mark.P1
def test_sort_products_by_name_a_to_z(driver, base_url):
    """
    Test that products can be sorted alphabetically from A to Z.
    
    Steps:
    1. Login with standard_user credentials
    2. Click on product sort dropdown
    3. Select Name (A to Z) option
    4. Verify products are sorted alphabetically A-Z
    5. Verify active option shows Name (A to Z)
    
    Expected Results:
    - Products are sorted alphabetically from A to Z
    - First product starts with earlier letter
    - Active option shows 'Name (A to Z)'
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
    active_option = products_page.get_active_sort_option()
    assert active_option == "Name (A to Z)", (
        f"Active sort option should be 'Name (A to Z)', but got '{active_option}'"
    )