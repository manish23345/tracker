import os
import json
import sys
import subprocess
import argparse
from typing import Dict, Any

from tracker import ProductTracker
from logger import logger
from colorama import Fore, Style, init

init(autoreset=True)

CONFIG_FILE = "config.json"

def create_default_config() -> None:
    """Creates a default config.json file if it does not exist."""
    default_config = {
        "telegram_bot_token": "YOUR_BOT_TOKEN",
        "telegram_chat_id": "YOUR_CHAT_ID",
        "check_interval": 60,
        "enable_price_alerts": True,
        "price_drop_threshold_percent": 1.0,
        "products": [
            {
                "name": "Sony PlayStation 5 Slim",
                "url": "https://www.amazon.in/dp/B0D1YG1PBL",
                "site": "amazon"
            },
            {
                "name": "Apple iPhone 15 Pro",
                "url": "https://www.flipkart.com/apple-iphone-15-pro-black-titanium-128-gb/p/itm5edaa9ab5b40d",
                "site": "flipkart"
            }
        ]
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        print(f"{Fore.GREEN}Created default {CONFIG_FILE}. Please edit it with your Telegram tokens and products.")
    except IOError as e:
        print(f"{Fore.RED}Error creating default config file: {e}")

def load_config() -> Dict[str, Any]:
    """Loads and parses the configuration file.

    Returns:
        A dictionary containing the configuration.
    """
    if not os.path.exists(CONFIG_FILE):
        create_default_config()
        sys.exit(0)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        # Basic validation
        if not config.get("products"):
            logger.warning("No products found in config.json. Add products to monitor.")
            
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing config.json: {e}")
        sys.exit(1)
    except IOError as e:
        logger.error(f"Error reading config.json: {e}")
        sys.exit(1)

def ensure_playwright_browsers() -> None:
    """Checks if Playwright chromium browser is installed; auto-installs it if missing."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright package not installed. Run: pip install -r requirements.txt")
        sys.exit(1)

    logger.info("Verifying Playwright browser installation...")
    try:
        with sync_playwright() as p:
            # Try to launch browser in headless mode to verify installation
            browser = p.chromium.launch(headless=True)
            browser.close()
        logger.info("Playwright browser verified successfully.")
    except Exception as e:
        error_msg = str(e)
        if "Executable doesn't exist" in error_msg or "playwright install" in error_msg.lower():
            logger.warning("Playwright Chromium browser not found. Attempting automatic installation...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.success("Playwright Chromium browser installed successfully.")
            except subprocess.CalledProcessError as err:
                logger.error(f"Automatic browser installation failed:\n{err.stderr}")
                logger.error("Please run the following command manually to install requirements:\nplaywright install chromium")
            except Exception as ex:
                logger.error(f"Error during browser installation: {ex}")
        else:
            logger.error(f"Unexpected Playwright startup error: {e}")

def main() -> None:
    """Main application entry point."""
    print(f"\n{Fore.GREEN}{Style.BRIGHT}=========================================")
    print(f"{Fore.GREEN}{Style.BRIGHT}   Amazon & Flipkart Stock Tracker")
    print(f"{Fore.GREEN}{Style.BRIGHT}=========================================\n")

    # Load configuration
    config = load_config()

    # Verify Telegram settings
    bot_token = config.get("telegram_bot_token", "")
    chat_id = config.get("telegram_chat_id", "")
    if not bot_token or bot_token == "YOUR_BOT_TOKEN" or not chat_id or chat_id == "YOUR_CHAT_ID":
        logger.warning(
            "Telegram is NOT configured. Alerts will only print to console.\n"
            "Update 'telegram_bot_token' and 'telegram_chat_id' in config.json to enable Telegram alerts."
        )

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Amazon & Flipkart Stock Tracker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the tracker once and exit (ideal for cron jobs/GitHub Actions)"
    )
    args = parser.parse_args()

    # Ensure browser binaries are available for playwright fallback
    ensure_playwright_browsers()

    # Initialize tracker and run
    tracker = ProductTracker(config, run_once=args.once)
    try:
        tracker.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Tracker stopped. Exiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
