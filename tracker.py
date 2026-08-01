import time
import sys
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List
from colorama import Fore, Style

from database import Database
from logger import logger, log_history_entry
from telegram_bot import TelegramBot
from scraper.utils import fetch_html
from scraper.amazon import AmazonScraper
from scraper.flipkart import FlipkartScraper

class ProductTracker:
    """Orchestrates the scraping, database checking, state transitions, and Telegram notifications."""

    def __init__(self, config: Dict[str, Any], run_once: bool = False) -> None:
        """Initializes the tracker with configuration settings.

        Args:
            config: Configuration dictionary loaded from config.json.
            run_once: If True, executes a single scan and then exits.
        """
        self.config = config
        self.db = Database()
        self.bot_token = config.get("telegram_bot_token", "")
        self.chat_id = config.get("telegram_chat_id", "")
        self.check_interval = config.get("check_interval", 60)
        self.enable_price_alerts = config.get("enable_price_alerts", True)
        self.price_drop_threshold = config.get("price_drop_threshold_percent", 1.0)
        self.enable_in_stock_reminders = config.get("enable_in_stock_reminders", True)
        self.products: List[Dict[str, str]] = config.get("products", [])
        self.run_once = run_once

    def run(self) -> None:
        """Starts the monitoring loop."""
        logger.info(f"Starting Stock Tracker with {len(self.products)} products.")
        logger.info(f"Check interval: {self.check_interval} seconds.")
        
        while True:
            # Poll Telegram Bot for any dynamically added products
            self._check_telegram_additions()

            start_time = datetime.now()
            next_scan_time = start_time + timedelta(seconds=self.check_interval)
            
            print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*60}")
            print(f"{Fore.CYAN}{Style.BRIGHT}Scan starting at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}\n")
            
            for idx, product in enumerate(self.products, 1):
                name = product.get("name", "Unknown Product")
                url = product.get("url", "")
                site = product.get("site", "").lower()
                
                # Print current progress cleanly
                progress_prefix = f"[{idx}/{len(self.products)}] {site.capitalize()}: {name}"
                sys.stdout.write(f"{Fore.BLUE}{progress_prefix} - {Fore.YELLOW}Checking... ")
                sys.stdout.flush()
                
                try:
                    self._check_product(product, progress_prefix)
                except Exception as e:
                    # Clean the inline message and log failure
                    sys.stdout.write(f"\r{Fore.BLUE}{progress_prefix} - {Fore.RED}FAILED\n")
                    sys.stdout.flush()
                    logger.error(f"Error checking product {name} ({site}): {e}", exc_info=True)
                
                # Small randomized delay between requests to prevent rate-limiting
                if idx < len(self.products):
                    time.sleep(random.uniform(2, 5))
            
            # Show completed scan
            print(f"\n{Fore.GREEN}{Style.BRIGHT}Scan completed. Log saved. Database updated.")
            
            if self.run_once:
                logger.info("Single scan run completed. Exiting.")
                break
                
            # Shutdown check or exit if run once (for debugging, standard is loop)
            self._countdown_timer(next_scan_time)

    def _check_product(self, product: Dict[str, str], progress_prefix: str) -> None:
        """Performs check for a single product.

        Args:
            product: Product metadata dictionary.
            progress_prefix: Output log prefix.
        """
        name = product.get("name", "Unknown Product")
        url = product.get("url", "")
        site = product.get("site", "").lower()
        
        # 1. Fetch HTML
        html = fetch_html(url, site)
        if not html:
            sys.stdout.write(f"\r{Fore.BLUE}{progress_prefix} - {Fore.RED}Fetch Failed (Skipping)\n")
            sys.stdout.flush()
            return

        # 2. Parse HTML depending on site
        if "amazon" in site:
            parsed_name, status, price = AmazonScraper.parse(html)
        elif "flipkart" in site:
            parsed_name, status, price = FlipkartScraper.parse(html)
        else:
            sys.stdout.write(f"\r{Fore.BLUE}{progress_prefix} - {Fore.RED}Unsupported Site '{site}'\n")
            sys.stdout.flush()
            return
            
        # Use config name if scraper failed to parse product title
        display_name = parsed_name if parsed_name else name

        # 3. Fetch past state
        past_state = self.db.get_product_state(url)
        
        prev_status = past_state.get("last_status") if past_state else None
        prev_price = past_state.get("last_price") if past_state else None
        
        status_color = Fore.RED if "Out" in status or "Unavailable" in status else Fore.GREEN
        sys.stdout.write(f"\r{Fore.BLUE}{progress_prefix} - {status_color}{status}")
        if price:
            sys.stdout.write(f" (Rs. {price:,.2f})")
        sys.stdout.write("\n")
        sys.stdout.flush()

        # Log history in multi-line format
        log_history_entry(site.capitalize(), display_name, status)
        
        # 4. Check for alerts
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        notify_triggered = False

        # Rule: Out of stock/unavailable/coming soon -> In stock transition OR reminder while in stock
        is_now_in_stock = status == "In Stock"
        was_previously_out = prev_status in [None, "Out of Stock", "Currently Unavailable", "Coming Soon"]
        
        if is_now_in_stock:
            if was_previously_out:
                logger.info(f"Alert Trigger: '{display_name}' is BACK IN STOCK!")
                sent = TelegramBot.send_notification(
                    token=self.bot_token,
                    chat_id=self.chat_id,
                    product_name=display_name,
                    status="Back in Stock",
                    price=price,
                    site_name=site.capitalize(),
                    url=url,
                    time_str=current_time_str,
                    alert_type="stock"
                )
                if sent:
                    notify_triggered = True
            elif self.enable_in_stock_reminders:
                logger.info(f"Alert Trigger: '{display_name}' is STILL IN STOCK (Reminder Alert)!")
                sent = TelegramBot.send_notification(
                    token=self.bot_token,
                    chat_id=self.chat_id,
                    product_name=display_name,
                    status="Still in Stock (Reminder)",
                    price=price,
                    site_name=site.capitalize(),
                    url=url,
                    time_str=current_time_str,
                    alert_type="reminder"
                )
                if sent:
                    notify_triggered = True

        # Rule: Price drop detection (only evaluated if no reminder was sent, to avoid double notifications)
        if is_now_in_stock and prev_status == "In Stock" and not notify_triggered and self.enable_price_alerts:
            if price is not None and prev_price is not None and price < prev_price:
                price_drop_pct = ((prev_price - price) / prev_price) * 100
                if price_drop_pct >= self.price_drop_threshold:
                    logger.info(f"Alert Trigger: Price drop of {price_drop_pct:.2f}% detected for '{display_name}'!")
                    sent = TelegramBot.send_notification(
                        token=self.bot_token,
                        chat_id=self.chat_id,
                        product_name=display_name,
                        status="In Stock",
                        price=price,
                        site_name=site.capitalize(),
                        url=url,
                        time_str=current_time_str,
                        alert_type="price_drop"
                    )
                    if sent:
                        notify_triggered = True

        # 5. Save updated state in database
        notify_timestamp = current_time_str if notify_triggered else (past_state.get("last_notified_at") if past_state else None)
        
        self.db.update_product_state(
            url=url,
            name=display_name,
            site=site,
            status=status,
            price=price,
            last_notified_at=notify_timestamp
        )

    def _countdown_timer(self, target_time: datetime) -> None:
        """Displays a countdown timer in place on the console until target_time.

        Args:
            target_time: Datetime object specifying when the next scan should run.
        """
        try:
            while True:
                remaining = target_time - datetime.now()
                seconds_left = int(remaining.total_seconds())
                if seconds_left <= 0:
                    break
                
                # Format MM:SS or simply SSs
                time_str = str(timedelta(seconds=seconds_left))
                # If duration starts with 0:, format it cleaner
                if time_str.startswith("0:"):
                    time_str = time_str[2:]
                
                sys.stdout.write(f"\r{Fore.YELLOW}Next scan in {time_str} ... (Press Ctrl+C to exit) ")
                sys.stdout.flush()
                time.sleep(1)
            # Clear line
            sys.stdout.write("\r" + " " * 70 + "\r")
            sys.stdout.flush()
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}Tracker stopped by user.")
            sys.exit(0)

    def _check_telegram_additions(self) -> None:
        """Polls Telegram Bot API for new product links sent by the user, and updates config.json dynamically."""
        if not self.bot_token or not self.chat_id:
            return

        last_update_id_str = self.db.get_metadata("last_telegram_update_id", "-1")
        last_update_id = int(last_update_id_str)

        api_url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"offset": last_update_id + 1, "timeout": 0}

        try:
            import requests
            import json
            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code != 200:
                return

            res_json = response.json()
            if not res_json.get("ok"):
                return

            updates = res_json.get("result", [])
            if not updates:
                return

            config_updated = False
            
            for update in updates:
                update_id = update.get("update_id")
                # Update the ID immediately so we don't process it again if parsing errors out
                if update_id > last_update_id:
                    last_update_id = update_id
                    self.db.set_metadata("last_telegram_update_id", str(last_update_id))

                message = update.get("message", {})
                chat = message.get("chat", {})
                sender_chat_id = str(chat.get("id", ""))
                
                # SECURITY: Only accept commands/links from the configured Chat ID!
                if sender_chat_id != str(self.chat_id):
                    continue

                text = message.get("text", "").strip()
                if not text:
                    continue

                # Look for links in the message text
                url_match = None
                for word in text.split():
                    if ("amazon.in/" in word or "flipkart.com/" in word) and word.startswith("http"):
                        url_match = word
                        break
                
                if url_match:
                    # Clean/normalize URL (remove tracking/query params)
                    url = url_match.split("?")[0]
                    site = "amazon" if "amazon" in url else "flipkart"
                    
                    # Check if already tracking
                    already_tracking = any(p.get("url") == url for p in self.products)
                    if already_tracking:
                        # Send confirmation reply
                        TelegramBot.send_notification(
                            token=self.bot_token,
                            chat_id=self.chat_id,
                            product_name="Product Link",
                            status="Already being monitored!",
                            price=None,
                            site_name=site.capitalize(),
                            url=url,
                            time_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            alert_type="reminder"
                        )
                        continue

                    # Create new product entry
                    new_product = {
                        "name": "Added via Telegram",
                        "url": url,
                        "site": site
                    }
                    
                    self.products.append(new_product)
                    config_updated = True
                    
                    logger.info(f"Dynamically added product from Telegram: {url}")
                    
                    # Send confirmation reply
                    TelegramBot.send_notification(
                        token=self.bot_token,
                        chat_id=self.chat_id,
                        product_name="New product added successfully!",
                        status="Now Tracking...",
                        price=None,
                        site_name=site.capitalize(),
                        url=url,
                        time_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        alert_type="stock"
                    )

            if config_updated:
                # Save updated list back to config.json
                self.config["products"] = self.products
                try:
                    with open("config.json", "w", encoding="utf-8") as f:
                        json.dump(self.config, f, indent=2)
                    logger.info("Saved updated config.json with new Telegram-added products.")
                except Exception as save_err:
                    logger.error(f"Failed to save config.json: {save_err}")

        except Exception as e:
            logger.error(f"Error checking Telegram bot commands: {e}")

