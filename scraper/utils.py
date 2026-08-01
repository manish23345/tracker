import time
import random
from typing import Dict, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from logger import logger

# List of realistic user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
]

def get_random_headers(site: str) -> Dict[str, str]:
    """Generates realistic headers for a given site.

    Args:
        site: The host/site name (e.g. 'amazon' or 'flipkart').

    Returns:
        A dictionary of headers.
    """
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    
    if "amazon" in site:
        headers.update({
            "Host": "www.amazon.in",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Device-Memory": "8",
        })
    elif "flipkart" in site:
        headers.update({
            "Host": "www.flipkart.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        })
        
    return headers

def fetch_html_requests(url: str, site: str, max_retries: int = 3) -> Tuple[Optional[str], bool]:
    """Fetches HTML content using requests with exponential backoff retry.

    Args:
        url: Target product URL.
        site: Site name ('amazon' or 'flipkart').
        max_retries: Maximum HTTP request attempts.

    Returns:
        A tuple of (html_content, is_blocked).
    """
    backoff = 2
    for attempt in range(1, max_retries + 1):
        try:
            headers = get_random_headers(site)
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=15)
            
            # Simple check for bot detection/blocking
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, "lxml")
                
                # Check for Amazon bot detection page
                if "amazon" in site:
                    # Amazon shows "To discuss automated access to Amazon data please contact" or robot check
                    if "api-services-support@amazon.com" in html or "type the characters you see below" in html.lower():
                        logger.warning(f"Amazon requests block detected (CAPTCHA/robot check) on attempt {attempt}.")
                        is_blocked = True
                        if attempt < max_retries:
                            sleep_time = backoff ** attempt + random.random()
                            time.sleep(sleep_time)
                            continue
                        return None, True
                
                # Check for Flipkart blocking
                if "flipkart" in site:
                    # Flipkart blocking can return blank page or redirect to error page
                    if len(html) < 2000 or "unusual traffic" in html.lower():
                        logger.warning(f"Flipkart requests block detected on attempt {attempt}.")
                        is_blocked = True
                        if attempt < max_retries:
                            sleep_time = backoff ** attempt + random.random()
                            time.sleep(sleep_time)
                            continue
                        return None, True
                
                return html, False
            
            elif response.status_code == 404:
                logger.error(f"Page not found (404) for URL: {url}")
                return None, False
                
            else:
                logger.warning(f"HTTP {response.status_code} on attempt {attempt} for URL: {url}")
                
        except requests.RequestException as e:
            logger.warning(f"Request exception on attempt {attempt} for URL: {url}: {e}")
        
        if attempt < max_retries:
            sleep_time = backoff ** attempt + random.random()
            logger.info(f"Retrying in {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
            
    return None, True

def fetch_html_playwright(url: str) -> Optional[str]:
    """Fetches HTML content using headless Playwright browser to bypass client side JS and standard blocks.

    Args:
        url: Target product URL.

    Returns:
        HTML string if successful, else None.
    """
    logger.info("Initializing Playwright fallback scraper...")
    is_flipkart = "flipkart" in url.lower()
    try:
        with sync_playwright() as p:
            # Launch headless chromium
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=random.choice(USER_AGENTS),
                locale="en-IN",
                timezone_id="Asia/Kolkata"
            )
            
            # Avoid basic playwright detection scripts
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()
            
            if is_flipkart:
                logger.info(f"Using Flipkart search-navigation bypass for URL: {url}")
                page.goto("https://www.flipkart.com/", wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2000)
                
                # Locate search input
                search_input = page.locator('input[name="q"]')
                if not search_input.count():
                    search_input = page.locator('input[placeholder*="Search"]')
                    
                if search_input.count():
                    search_input.first.fill(url)
                    page.wait_for_timeout(1000)
                    search_input.first.press("Enter")
                    page.wait_for_timeout(4000)
                    
                    # Find links containing product path
                    product_links = page.locator('a[href*="/p/"]')
                    if product_links.count():
                        logger.info("Found product search results. Simulating click...")
                        try:
                            # Typically opens in a new tab/popup
                            with context.expect_page(timeout=10000) as new_page_info:
                                product_links.first.click()
                            new_page = new_page_info.value
                            new_page.wait_for_load_state("networkidle", timeout=30000)
                            new_page.wait_for_timeout(3000)
                            html = new_page.content()
                            browser.close()
                            return html
                        except Exception as click_err:
                            logger.warning(f"Popup navigation failed, checking current tab: {click_err}")
                            page.wait_for_load_state("domcontentloaded")
                            html = page.content()
                            browser.close()
                            return html
                    else:
                        logger.warning("No product links found on search results page. Trying direct navigation...")
                else:
                    logger.warning("Search input not found on Flipkart homepage. Trying direct navigation...")

            # Direct navigation fallback (for Amazon or if Flipkart search failed)
            logger.info(f"Navigating to {url} directly via Playwright...")
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            # Extra wait for dynamic javascript elements to populate
            page.wait_for_timeout(random.randint(2000, 4000))
            
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.error(f"Playwright rendering failed: {e}")
        return None

def fetch_html(url: str, site: str, force_playwright: bool = False) -> Optional[str]:
    """Fetches HTML content, trying requests first and automatically falling back to Playwright if blocked.

    Args:
        url: Target product URL.
        site: Site name ('amazon' or 'flipkart').
        force_playwright: Force run playwright without trying requests first.

    Returns:
        HTML string if successful, else None.
    """
    if force_playwright:
        return fetch_html_playwright(url)

    html, is_blocked = fetch_html_requests(url, site)
    if html:
        return html
    
    if is_blocked:
        logger.warning("Requests blocked or failed. Falling back to Playwright headless browser...")
        return fetch_html_playwright(url)
        
    return None
