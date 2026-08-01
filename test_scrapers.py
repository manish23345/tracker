import unittest
from scraper.amazon import AmazonScraper
from scraper.flipkart import FlipkartScraper

class TestScrapers(unittest.TestCase):
    """Unit tests for testing Amazon & Flipkart scrapers with mock HTML."""

    def test_amazon_in_stock(self) -> None:
        mock_html = """
        <html>
            <body>
                <span id="productTitle">Sony PlayStation 5 Console</span>
                <span class="a-price-whole">54,990.00</span>
                <div id="availability">
                    <span>In Stock</span>
                </div>
            </body>
        </html>
        """
        name, status, price = AmazonScraper.parse(mock_html)
        self.assertEqual(name, "Sony PlayStation 5 Console")
        self.assertEqual(status, "In Stock")
        self.assertEqual(price, 54990.0)

    def test_amazon_out_of_stock(self) -> None:
        mock_html = """
        <html>
            <body>
                <span id="productTitle">Out of Stock Item</span>
                <div id="availability">
                    <span>Currently unavailable.</span>
                </div>
            </body>
        </html>
        """
        name, status, price = AmazonScraper.parse(mock_html)
        self.assertEqual(name, "Out of Stock Item")
        self.assertEqual(status, "Currently Unavailable")
        self.assertIsNone(price)

    def test_flipkart_in_stock(self) -> None:
        mock_html = """
        <html>
            <body>
                <span class="B_NuCI">Apple iPhone 15 Pro (Black, 128 GB)</span>
                <div class="_30jeq3">₹1,27,990</div>
                <button class="_2KpZ6l _2U9uOA _3v1-ww">ADD TO CART</button>
            </body>
        </html>
        """
        name, status, price = FlipkartScraper.parse(mock_html)
        self.assertEqual(name, "Apple iPhone 15 Pro (Black, 128 GB)")
        self.assertEqual(status, "In Stock")
        self.assertEqual(price, 127990.0)

    def test_flipkart_out_of_stock(self) -> None:
        mock_html = """
        <html>
            <body>
                <span class="B_NuCI">Sony Alpha 7M4 Camera</span>
                <div class="_16FRp0">This item is currently out of stock.</div>
            </body>
        </html>
        """
        name, status, price = FlipkartScraper.parse(mock_html)
        self.assertEqual(name, "Sony Alpha 7M4 Camera")
        self.assertEqual(status, "Out of Stock")
        self.assertIsNone(price)

if __name__ == "__main__":
    unittest.main()
