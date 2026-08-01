# Amazon & Flipkart Telegram Stock Tracker

A reliable, feature-rich Python application designed to track product availability on Amazon India (`amazon.in`) and Flipkart, sending instant notification alerts via Telegram when products come back in stock or undergo price drops.

---

## Features

- **Multi-URL Monitoring**: Track multiple products concurrently.
- **Robust Scrapers**: Fast and clean extraction using `requests` + `BeautifulSoup`.
- **Playwright Fallback**: Automatically spins up a headless Chromium browser using Playwright to handle anti-bot protection or dynamic JS-rendered stock details.
- **State Management**: Persists previous price and availability state in an SQLite database (`tracker.db`) to avoid duplicate alerts.
- **Price Tracking**: Detects price changes and alerts you of price drops based on a customizable percentage threshold.
- **Colorized Output**: Real-time monitoring stats and countdown timers in the terminal.
- **Dual Logging**: Writes debugging details to `tracker.log`, and product status updates to `history.log` in the requested format.

---

## Installation

### Prerequisites
- Python 3.11 or higher
- Pip (Python Package Installer)

### 1. Clone or Copy the Repository
Navigate to the project root directory.

### 2. Install Python Dependencies
Install the required packages listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Initialize Playwright Browser Binaries
Playwright requires browser binaries to execute. Run the command below to download Chromium:
```bash
playwright install chromium
```
*(Note: If you skip this, the program will attempt to auto-install it on its first launch.)*

---

## Setting Up Telegram Bot

To receive instant notification alerts, you will need a Telegram Bot and your personal Chat ID:

### Step 1: Create a Bot via BotFather
1. Open the Telegram app and search for [@BotFather](https://t.me/BotFather).
2. Start a chat and send the `/newbot` command.
3. Choose a name and a username for your bot.
4. Copy the API **HTTP API Access Token** (looks like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`). Keep this private!

### Step 2: Get Your Chat ID
To send messages, the bot needs your chat ID.
1. Search for [@userinfobot](https://t.me/userinfobot) on Telegram.
2. Send any message or `/start`.
3. It will reply with your `Id` (a 9 or 10-digit number like `987654321`). Copy this value.
4. **Important**: Start a conversation with your bot by clicking its name and clicking **Start**. The bot cannot send you messages unless you start the conversation first.

---

## Configuration

Edit the automatically generated `config.json` file in the project root:

```json
{
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "check_interval": 60,
  "enable_price_alerts": true,
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
```

### Configuration Fields
- `telegram_bot_token`: Your Telegram bot token from BotFather.
- `telegram_chat_id`: Your Telegram chat ID.
- `check_interval`: Pause duration between scans (in seconds). It is recommended to keep this at `300` (5 minutes) or more for long-term production.
- `enable_price_alerts`: Set to `true` to notify on price drops.
- `price_drop_threshold_percent`: Notify only if the price drop is equal to or greater than this percentage.
- `products`: Array of items to monitor.
  - `name`: Human-readable identifier.
  - `url`: Product link.
  - `site`: Must be either `"amazon"` or `"flipkart"`.

---

## Running the Tracker

To run the tracker, execute `main.py` using your Python interpreter:

```bash
python main.py
```

To stop execution at any time, press `Ctrl+C`.

---

## Deployment Guides

### 1. Windows (Task Scheduler or Background Execution)
- Create a batch script `run_tracker.bat`:
  ```bat
  @echo off
  cd /d "C:\path\to\StockTracker"
  python main.py
  pause
  ```
- Alternatively, search for **Task Scheduler**, create a Basic Task, select "When I log on" as the trigger, and point the action to your script or `pythonw.exe main.py` (which runs without opening a CMD window).

### 2. Linux (systemd Service)
For reliable 24/7 hosting on a Linux server or VPS:
1. Create a systemd service file:
   ```bash
   sudo nano /etc/systemd/system/stocktracker.service
   ```
2. Paste the configuration:
   ```ini
   [Unit]
   Description=Telegram Stock Tracker Service
   After=network.target

   [Service]
   Type=simple
   User=yourusername
   WorkingDirectory=/home/yourusername/StockTracker
   ExecStart=/usr/bin/python3 main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable stocktracker
   sudo systemctl start stocktracker
   ```
4. View service status and logs:
   ```bash
   sudo systemctl status stocktracker
   journalctl -u stocktracker -f
   ```

### 3. Raspberry Pi (Raspbian OS)
Ensure you install necessary headless system dependencies for Playwright:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
```
Then use `tmux`, `screen`, or a `systemd` service to keep the process running in the background.

### 4. GitHub Actions (Cron Jobs)
If you want to run the tracker using GitHub Actions:
1. Create a `.github/workflows/tracker.yml` file in your repository.
2. Example script:
   ```yaml
   name: Stock Tracker

   on:
     schedule:
       # Run once every hour
       - cron: '0 * * * *'
     workflow_dispatch:

   jobs:
     track:
       runs-on: ubuntu-latest
       steps:
       - name: Check out repo
         uses: actions/checkout@v4

       - name: Set up Python
         uses: actions/setup-python@v5
         with:
           python-format: '3.11'
           cache: 'pip'

       - name: Install dependencies
         run: |
           pip install -r requirements.txt
           playwright install chromium

       - name: Run tracker (Single Check Mode)
         env:
           TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
           TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
         run: |
           # You can modify main.py to read token from environment variables if running as a pipeline
           python main.py
   ```
   *(Note: Since GitHub runner IPs are static and widely used, they are highly likely to face aggressive blocking on Amazon/Flipkart. It is highly recommended to host the tracker on a residential connection or private server.)*
