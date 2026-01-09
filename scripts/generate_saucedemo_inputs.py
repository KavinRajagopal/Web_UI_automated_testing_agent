#!/usr/bin/env python3
"""Pre-generate SauceDemo inputs for the demo.

This script:
1. Discovers UI elements from saucedemo.com pages using Selenium
2. Generates test cases using Claude via Bedrock
3. Saves all outputs to inputs/saucedemo/

Run with: venv/bin/python scripts/generate_saucedemo_inputs.py

Requirements:
- Chrome browser installed
- AWS credentials configured (profile: bedrock-user)
- Dependencies installed (pip install -r requirements.txt)
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.bedrock_client import BedrockClient
from src.tools.element_discovery import ElementDiscoveryTool, discover_saucedemo_pages
from src.tools.testcase_generator import (
    TestCaseGenerator,
    export_testcases_to_csv,
    export_pages_to_json
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_output_dirs(base_path: str) -> dict:
    """Create output directory structure."""
    dirs = {
        "root": base_path,
        "element_metadata": os.path.join(base_path, "element_metadata"),
        "screenshots": os.path.join(base_path, "screenshots"),
    }
    
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")
    
    return dirs


def create_module_spec(output_dir: str) -> str:
    """Create module_spec.json for saucedemo."""
    module_spec = {
        "module_name": "saucedemo",
        "app_name": "SauceDemo",
        "app_url": "https://www.saucedemo.com",
        "environment": "production",
        "browser": "chrome",
        "selector_priority": ["data-testid", "id", "name", "aria-label"],
        "avoid_selectors": ["css", "xpath"],
        "description": "E-commerce demo site for Selenium testing",
        "pages": [
            {
                "name": "LoginPage",
                "url_pattern": "/",
                "element_metadata_file": "element_metadata/loginpage.json"
            },
            {
                "name": "ProductsPage", 
                "url_pattern": "/inventory.html",
                "element_metadata_file": "element_metadata/productspage.json"
            },
            {
                "name": "CartPage",
                "url_pattern": "/cart.html",
                "element_metadata_file": "element_metadata/cartpage.json"
            },
            {
                "name": "CheckoutPage",
                "url_pattern": "/checkout-step-one.html",
                "element_metadata_file": "element_metadata/checkoutpage.json"
            }
        ],
        "test_credentials": {
            "standard_user": {
                "username": "standard_user",
                "password": "secret_sauce"
            },
            "locked_out_user": {
                "username": "locked_out_user",
                "password": "secret_sauce"
            },
            "problem_user": {
                "username": "problem_user",
                "password": "secret_sauce"
            }
        },
        "created_at": datetime.now().isoformat()
    }
    
    output_path = os.path.join(output_dir, "module_spec.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(module_spec, f, indent=2)
    
    logger.info(f"Created module_spec.json: {output_path}")
    return output_path


def run_element_discovery(output_dirs: dict, take_screenshots: bool = True) -> list:
    """
    Run element discovery on saucedemo.com.
    
    Args:
        output_dirs: Dict with output directory paths
        take_screenshots: Whether to capture screenshots
        
    Returns:
        List of PageMetadata objects
    """
    logger.info("=" * 60)
    logger.info("STEP 1: Element Discovery")
    logger.info("=" * 60)
    
    tool = ElementDiscoveryTool(headless=True)
    screenshots = {}
    pages = []
    
    try:
        tool.start_browser()
        
        # 1. Login Page
        logger.info("Discovering LoginPage...")
        login_page = tool.discover_page(
            url="https://www.saucedemo.com",
            page_name="LoginPage",
            description="SauceDemo login page with username/password authentication"
        )
        pages.append(login_page)
        
        if take_screenshots:
            screenshot = tool.take_screenshot()
            if screenshot:
                screenshots["LoginPage"] = screenshot
                screenshot_path = os.path.join(output_dirs["screenshots"], "login_page.png")
                with open(screenshot_path, 'wb') as f:
                    f.write(screenshot)
                logger.info(f"Saved screenshot: {screenshot_path}")
        
        # 2. Log in
        logger.info("Logging in with standard_user...")
        driver = tool.driver
        
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        driver.find_element(By.CSS_SELECTOR, "[data-test='username']").send_keys("standard_user")
        driver.find_element(By.CSS_SELECTOR, "[data-test='password']").send_keys("secret_sauce")
        driver.find_element(By.CSS_SELECTOR, "[data-test='login-button']").click()
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='inventory-container']"))
        )
        
        # 3. Products Page
        logger.info("Discovering ProductsPage...")
        products_page = tool.discover_page(
            url=driver.current_url,
            page_name="ProductsPage",
            description="SauceDemo products/inventory listing page"
        )
        pages.append(products_page)
        
        if take_screenshots:
            screenshot = tool.take_screenshot()
            if screenshot:
                screenshots["ProductsPage"] = screenshot
                screenshot_path = os.path.join(output_dirs["screenshots"], "products_page.png")
                with open(screenshot_path, 'wb') as f:
                    f.write(screenshot)
        
        # 4. Add item and go to cart
        import time
        try:
            logger.info("Adding item to cart...")
            time.sleep(1)  # Wait for page to stabilize
            add_btn = driver.find_element(By.CSS_SELECTOR, "[data-test^='add-to-cart']")
            add_btn.click()
            time.sleep(1)
            
            logger.info("Navigating to cart...")
            cart_link = driver.find_element(By.CSS_SELECTOR, "[data-test='shopping-cart-link']")
            cart_link.click()
            time.sleep(2)  # Give time for navigation
            
            # 5. Cart Page
            logger.info("Discovering CartPage...")
            cart_page = tool.discover_page(
                url=driver.current_url,
                page_name="CartPage",
                description="SauceDemo shopping cart page"
            )
            pages.append(cart_page)
            
            if take_screenshots:
                screenshot = tool.take_screenshot()
                if screenshot:
                    screenshots["CartPage"] = screenshot
                    screenshot_path = os.path.join(output_dirs["screenshots"], "cart_page.png")
                    with open(screenshot_path, 'wb') as f:
                        f.write(screenshot)
            
            # 6. Go to checkout
            logger.info("Going to checkout...")
            time.sleep(1)
            checkout_btn = driver.find_element(By.CSS_SELECTOR, "[data-test='checkout']")
            checkout_btn.click()
            time.sleep(2)  # Give time for navigation
            
            # 7. Checkout Page
            logger.info("Discovering CheckoutPage...")
            checkout_page = tool.discover_page(
                url=driver.current_url,
                page_name="CheckoutPage",
                description="SauceDemo checkout information page"
            )
            pages.append(checkout_page)
            
            if take_screenshots:
                screenshot = tool.take_screenshot()
                if screenshot:
                    screenshots["CheckoutPage"] = screenshot
                    screenshot_path = os.path.join(output_dirs["screenshots"], "checkout_page.png")
                    with open(screenshot_path, 'wb') as f:
                        f.write(screenshot)
        except Exception as e:
            logger.warning(f"Could not complete cart/checkout discovery: {e}")
            logger.info("Continuing with discovered pages...")
        
        # Export page metadata to JSON
        logger.info("Exporting page metadata...")
        export_pages_to_json(pages, output_dirs["element_metadata"])
        
        # Print summary
        logger.info("-" * 40)
        logger.info("Element Discovery Summary:")
        for page in pages:
            logger.info(f"  {page.page_name}: {len(page.elements)} elements")
        logger.info("-" * 40)
        
        return pages, screenshots
        
    finally:
        tool.close_browser()


def run_testcase_generation(pages: list, screenshots: dict, output_dir: str) -> list:
    """
    Generate test cases using LLM.
    
    Args:
        pages: List of PageMetadata objects
        screenshots: Dict of page_name -> screenshot bytes
        output_dir: Output directory path
        
    Returns:
        List of TestCaseRow objects
    """
    logger.info("=" * 60)
    logger.info("STEP 2: Test Case Generation")
    logger.info("=" * 60)
    
    # Initialize Bedrock client
    logger.info("Initializing Bedrock client...")
    llm_client = BedrockClient(
        profile_name="tring-kavin",
        region_name="us-east-2"
    )
    
    # Create generator
    generator = TestCaseGenerator(llm_client, max_tests_per_page=8)
    
    # Generate test cases with saucedemo-specific coverage hints
    # Note: Skipping screenshots due to image processing issues
    logger.info("Generating test cases with LLM...")
    test_cases = generator.generate_for_saucedemo(pages, screenshots=None)
    
    # Export to CSV
    csv_path = os.path.join(output_dir, "testcases.csv")
    export_testcases_to_csv(test_cases, csv_path)
    
    # Print summary
    logger.info("-" * 40)
    logger.info("Test Case Generation Summary:")
    logger.info(f"  Total test cases: {len(test_cases)}")
    
    # Group by module/page
    by_page = {}
    for tc in test_cases:
        page = tc.page_name or "Unknown"
        by_page[page] = by_page.get(page, 0) + 1
    
    for page, count in by_page.items():
        logger.info(f"  {page}: {count} test cases")
    
    # Print LLM usage
    usage = llm_client.get_usage_stats()
    logger.info(f"  LLM calls: {usage['call_count']}")
    logger.info(f"  Total tokens: {usage['total_tokens']:,}")
    logger.info("-" * 40)
    
    return test_cases


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("SauceDemo Input Generator")
    logger.info("=" * 60)
    
    # Setup output directory
    output_base = os.path.join(project_root, "inputs", "saucedemo")
    output_dirs = create_output_dirs(output_base)
    
    # Create module_spec.json
    create_module_spec(output_base)
    
    # Step 1: Element Discovery
    pages, screenshots = run_element_discovery(output_dirs, take_screenshots=True)
    
    # Step 2: Test Case Generation
    test_cases = run_testcase_generation(pages, screenshots, output_base)
    
    # Final summary
    logger.info("=" * 60)
    logger.info("GENERATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Output directory: {output_base}")
    logger.info("Generated files:")
    logger.info(f"  - module_spec.json")
    logger.info(f"  - testcases.csv ({len(test_cases)} test cases)")
    logger.info(f"  - element_metadata/ ({len(pages)} page files)")
    logger.info(f"  - screenshots/ ({len(screenshots)} images)")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
