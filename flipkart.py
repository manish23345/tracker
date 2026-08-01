import re
from typing import Tuple, Optional
from bs4 import BeautifulSoup
from logger import logger

class FlipkartScraper:
    """Scraper for extracting product details from Flipkart India."""

    @staticmethod
    def clean_price(price_str: str) -> Optional[float]:
        """Cleans price string and converts it to a float.

        Args:
            price_str: Raw price string (e.g. '₹49,999').

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
        """Parses Flipkart product HTML page.

        Args:
            html: HTML source of the product page.

        Returns:
            A tuple of (Product Name, Status, Price).
            Status is one of: "In Stock", "Out of Stock", "Currently Unavailable", "Coming Soon".
        """
        soup = BeautifulSoup(html, "lxml")

        # 1. Product Name extraction
        # Try multiple common Flipkart title classes/selectors
        name_selectors = [
            ".B_NuCI",      # Traditional/Common layout title class
            ".VU-ZEg",      # Newer mobile/web layout title class
            "h1",           # General fallback h1
        ]
        name = None
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem:
                name = name_elem.get_text(strip=True)
                break

        # 2. Price extraction
        price = None
        # Flipkart's price div classes typically have currency symbol and bold text
        price_selectors = [
            "._30jeq3",     # Traditional price class
            "._30jeq3._16Jk1d",
            ".Nx9r8q",      # Newer layout price class
            "div[class*='_30jeq3']",
            "div[class*='Nx9r8q']"
        ]
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                raw_price = price_elem.get_text(strip=True)
                parsed = cls.clean_price(raw_price)
                if parsed:
                    price = parsed
                    break

        # 3. Status extraction
        # Default status is "In Stock" if we find buy buttons, otherwise we assess.
        status = "Out of Stock"
        
        # Check for Add to Cart or Buy Now buttons (using classes or text content)
        buttons = soup.find_all("button")
        has_buy_buttons = False
        for btn in buttons:
            btn_text = btn.get_text(strip=True).upper()
            if "ADD TO CART" in btn_text or "BUY NOW" in btn_text:
                has_buy_buttons = True
                break

        # Check links that act as buy buttons (Flipkart sometimes uses <a> for Buy Now)
        links = soup.find_all("a")
        for link in links:
            link_text = link.get_text(strip=True).upper()
            if "ADD TO CART" in link_text or "BUY NOW" in link_text:
                has_buy_buttons = True
                break

        # Inspect out-of-stock overlay messages
        out_of_stock_selectors = [
            "._1V415g",     # Common "Sold Out" banner class
            "._16FRp0",     # "This item is currently out of stock" class
            "._1A1M7F",
            "div[class*='_1V415g']",
            "div[class*='_16FRp0']"
        ]
        
        oos_message = ""
        for selector in out_of_stock_selectors:
            elem = soup.select_one(selector)
            if elem:
                oos_message += " " + elem.get_text(strip=True).lower()

        # Or search raw HTML text body if specific divs aren't found
        page_text = soup.get_text().lower()

        if has_buy_buttons and "sold out" not in oos_message and "out of stock" not in oos_message:
            status = "In Stock"
        elif "coming soon" in oos_message or "coming soon" in page_text:
            status = "Coming Soon"
        elif "sold out" in oos_message or "sold out" in page_text:
            status = "Out of Stock"
        elif "out of stock" in oos_message or "currently unavailable" in page_text:
            status = "Out of Stock"
        elif has_buy_buttons:
            status = "In Stock"
        else:
            # If no buy buttons are found and price is absent, it is highly likely Out of Stock
            if price:
                status = "In Stock"
            else:
                status = "Out of Stock"

        # Log findings for developer diagnostics
        logger.debug(f"Parsed Flipkart: Name={name}, Status={status}, Price={price}")
        return name, status, price
