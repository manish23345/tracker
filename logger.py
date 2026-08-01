import logging
import os
import sys
from datetime import datetime
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored terminal output
init(autoreset=True)

# Standard logging configuration for system events
LOG_FILE = "tracker.log"
HISTORY_FILE = "history.log"

# Create a logger for the application
logger = logging.getLogger("StockTracker")
logger.setLevel(logging.INFO)

# Formatter for standard logs
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# File handler for system logs
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console handler with color support
class ColoredConsoleHandler(logging.StreamHandler):
    """Custom logging handler that adds colors to the console output."""
    def emit(self, record):
        try:
            message = self.format(record)
            # Safe-encode to console's encoding to avoid UnicodeEncodeError on Windows CP1252
            encoding = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
            if not encoding:
                encoding = 'utf-8'
            safe_message = message.encode(encoding, errors='replace').decode(encoding)
            
            if record.levelno >= logging.ERROR:
                print(f"{Fore.RED}{Style.BRIGHT}{safe_message}")
            elif record.levelno >= logging.WARNING:
                print(f"{Fore.YELLOW}{safe_message}")
            elif "SUCCESS" in record.levelname:
                print(f"{Fore.GREEN}{safe_message}")
            else:
                print(f"{Fore.WHITE}{safe_message}")
        except Exception:
            self.handleError(record)

console_handler = ColoredConsoleHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Add custom level SUCCESS
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")

def log_success(message, *args, **kws):
    if logger.isEnabledFor(SUCCESS_LEVEL_NUM):
        logger._log(SUCCESS_LEVEL_NUM, message, args, **kws)

logger.success = log_success

def log_history_entry(site: str, name: str, status: str) -> None:
    """Logs the product status to a history file in the required multi-line format:
    
    YYYY-MM-DD HH:MM
    Site
    Product Name
    Status
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"{timestamp}\n{site}\n{name}\n{status}\n\n"
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except IOError as e:
        logger.error(f"Failed to write to history log: {e}")
