from typing import Optional
import requests
from logger import logger

class TelegramBot:
    """Handles communication with the Telegram Bot API."""

    @staticmethod
    def send_notification(
        token: str,
        chat_id: str,
        product_name: str,
        status: str,
        price: Optional[float],
        site_name: str,
        url: str,
        time_str: str,
        alert_type: str = "stock"
    ) -> bool:
        """Sends a structured stock alert notification to the specified chat.

        Args:
            token: Telegram Bot API Token.
            chat_id: Telegram Chat ID to send messages to.
            product_name: The name of the product.
            status: The status of the product (e.g. Back in Stock).
            price: The current price of the product.
            site_name: The name of the store ('Amazon' or 'Flipkart').
            url: The product URL.
            time_str: Timestamp of the check.
            alert_type: Type of alert ('stock' or 'price_drop').

        Returns:
            True if sent successfully, False otherwise.
        """
        if not token or token == "YOUR_BOT_TOKEN" or not chat_id or chat_id == "YOUR_CHAT_ID":
            logger.warning("Telegram Bot Token or Chat ID is not configured. Skipping notification.")
            return False

        price_display = f"₹{price:,.2f}" if price is not None else "Not Available"
        
        if alert_type == "price_drop":
            title = "📉 PRICE DROP ALERT!"
            status_indicator = f"💰 Price Reduced"
        else:
            title = "🚨 STOCK ALERT!"
            status_indicator = f"✅ {status}"

        # Construct message text with Markdown formatting
        # Note: HTML tags or clean Markdown can be used, HTML is safer from parsing errors with special chars.
        message = (
            f"<b>{title}</b>\n\n"
            f"<b>Product:</b> {product_name}\n"
            f"<b>Status:</b> {status_indicator}\n"
            f"<b>Price:</b> {price_display}\n"
            f"<b>Store:</b> {site_name}\n"
            f"<b>Time:</b> {time_str}\n\n"
            f"<b>Link:</b>\n{url}"
        )

        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        try:
            response = requests.post(api_url, json=payload, timeout=15)
            response_json = response.json()
            if response.status_code == 200 and response_json.get("ok"):
                logger.success(f"Telegram notification sent successfully for '{product_name}'")
                return True
            else:
                logger.error(
                    f"Failed to send Telegram message. HTTP {response.status_code}, Response: {response.text}"
                )
                return False
        except requests.RequestException as e:
            logger.error(f"Network error trying to contact Telegram API: {e}")
            return False
