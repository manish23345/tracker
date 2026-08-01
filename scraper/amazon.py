import re
from typing import Tuple, Optional
from bs4 import BeautifulSoup
from logger import logger

class AmazonScraper:
    """Scraper for extracting product details from Amazon India."""

    @staticmethod
    def clean_price(price_str: str) -> Optional[float]:
        """Cleans price string and converts it to a float.

        Args:
            price_str: Raw price string (e.g. '₹49,999.00').

        Returns:
            Float value if successfully parsed, else None.
        """
        if not price_str:
            return None
        # Remove currency symbols, commas, and other non-digit/dot characters
        cleaned = re.sub(r"[^\d.]", "", price_str)
        try:
            return float(cleaned)
        except ValueError:
            return None

    @classmethod
    def parse(cls, html: str) -> Tuple[Optional[str], str, Optional[float]]:
        """Parses Amazon product HTML page.

        Args:
            html: HTML source of the product page.

        Returns:
            A tuple of (Product Name, Status, Price).
            Status is one of: "In Stock", "Out of Stock", "Currently Unavailable", "Coming Soon".
        """
        soup = BeautifulSoup(html, "lxml")

        # 1. Product Name extraction
        name_elem = soup.find(id="productTitle")
        name = name_elem.get_text(strip=True) if name_elem else None
        
        # 2. Price extraction
        price = None
        
        # Try different selectors for pricing (Amazon uses various elements based on layout/deals)
        price_selectors = [
            (".a-price-whole", False), # Usually contains the main price text
            (".apexPriceToPay .a-offscreen", False),
            ("#priceblock_ourprice", False),
            ("#priceblock_dealprice", False),
            (".priceToPay .a-offscreen", False),
            (".a-price .a-offscreen", False),
            ("#kindle-price-reading-button-text", False),
        ]
        
        for selector, is_text_only in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                raw_price = price_elem.get_text(strip=True)
                # Sometimes .a-price-whole has a dot or weird characters at the end, clean it
                parsed = cls.clean_price(raw_price)
                if parsed:
                    price = parsed
                    break

        # 3. Status extraction
        status = "Currently Unavailable" # Default fallback
        
        availability_elem = soup.select_one("#availability")
        availability_text = availability_elem.get_text(strip=True).lower() if availability_elem else ""
        
        # Check explicit availability text keywords
        if "currently unavailable" in availability_text:
            status = "Currently Unavailable"
        elif "out of stock" in availability_text or "temporarily out of stock" in availability_text:
            status = "Out of Stock"
        elif "coming soon" in availability_text:
            status = "Coming Soon"
        elif "in stock" in availability_text or "available" in availability_text or "left in stock" in availability_text:
            status = "In Stock"
        else:
            # Fallback checks based on DOM elements
            add_to_cart = soup.find(id="add-to-cart-button")
            buy_now = soup.find(id="buy-now-button")
            
            if add_to_cart or buy_now:
                status = "In Stock"
            elif soup.find(id="outOfStock"):
                status = "Out of Stock"
            elif "select delivery location to see product availability" in availability_text:
                # If location issue, check if price or cart button exists
                if price or add_to_cart:
                    status = "In Stock"
                else:
                    status = "Currently Unavailable"

        # Log findings for developer diagnostics
        logger.debug(f"Parsed Amazon: Name={name}, Status={status}, Price={price}")
        return name, status, price
