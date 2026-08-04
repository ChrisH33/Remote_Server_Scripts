"""
DeskAllocator.py
----------------
Entry point for the Desk Allocator.

Lifecycle
---------
1.  Authenticate with Google Sheets.
2.  Post a Slack startup notice.
3.  Loop every `refresh_rate` seconds:
      a. Fetch desk allocation data from the Google Sheet.
      b. Format and send the data to Slack.
4.  On clean exit (SIGTERM, SIGINT, or dev-mode break) post a shutdown
    notice to Slack so the team knows the allocator is no longer running.

Dev / non-Linux behaviour
--------------------------
On non-Linux machines `prod_mode()` returns False and the loop runs exactly
once.  This lets you test locally without an infinite loop.
"""

# std modules
import signal
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Setup path and load environment
sys.path.append(str(Path(__file__).parent.parent.resolve()))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# universal imports
from utils.config import logger, prod_mode
from utils.slack_wrapper import SlackClientWrapper

# local imports
from config import load_var
from BuildSheetsService import build_sheets_service
from GetFromSheets import get_desk_allocations
from SendToSlack import send_desk_allocations

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

_shutdown_requested = False


def _request_shutdown(signum, frame):
    global _shutdown_requested
    logger.info(f"Received signal {signum} — shutting down after current cycle.")
    _shutdown_requested = True


signal.signal(signal.SIGTERM, _request_shutdown)
signal.signal(signal.SIGINT,  _request_shutdown)

# ---------------------------------------------------------------------------
# Initialise config, Slack and Google Sheets
# ---------------------------------------------------------------------------

Config = load_var()
slack  = SlackClientWrapper(bot_token=Config.slack_bot_token)
service = build_sheets_service(Config)

# Post startup message
slack.send_message(channel=Config.channel_id, text=Config.startup_message)

# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def retry(func, *args, retries: int = 3, delay: float = 2.0, **kwargs):
    """
    Call `func(*args, **kwargs)` up to `retries` times, waiting `delay`
    seconds between attempts.

    Returns the function's return value on success, or None after all
    retries are exhausted.
    """
    for attempt in range(1, retries + 1):
        try:
            result = func(*args, **kwargs)
            if result is not None:
                return result
            logger.warning(
                f"Attempt {attempt}/{retries} failed for {func.__name__}: returned None"
            )
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{retries} failed for {func.__name__}: {e}")
        
        if attempt < retries:
            time.sleep(delay)

    logger.error(f"{func.__name__} failed after {retries} attempts")
    return None

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

# Track previous message timestamp to update instead of spamming channel
previous_message_ts = None

try:
    while not _shutdown_requested:
        # ── Fetch desk allocations from Google Sheets ─────────────────────
        allocations = retry(
            get_desk_allocations,
            service, Config.spreadsheet_id, Config.sheet_name,
            retries=3, delay=2,
        )

        if allocations is None:
            logger.error("Failed to fetch desk allocations after retries")
            time.sleep(Config.refresh_rate)
            continue

        # ── Send to Slack ─────────────────────────────────────────────────
        # Option 1: Send a new message each time
        # ts = retry(
        #     send_desk_allocations,
        #     slack, Config.channel_id, allocations,
        #     retries=3, delay=2,
        # )

        # Option 2: Update the same message each time (recommended)
        if previous_message_ts:
            # Update existing message
            from SendToSlack import format_desk_allocation_message
            blocks = format_desk_allocation_message(allocations)
            
            success = retry(
                slack.update_message,
                message_ts=previous_message_ts,
                channel=Config.channel_id,
                text="Desk Allocations Update",
                blocks=blocks,
                retries=3, delay=2,
            )
            
            if not success:
                logger.error("Failed to update Slack message")
        else:
            # Send initial message and save timestamp
            previous_message_ts = retry(
                send_desk_allocations,
                slack, Config.channel_id, allocations,
                retries=3, delay=2,
            )
            
            if not previous_message_ts:
                logger.error("Failed to send initial desk allocations")

        # ── Break after one cycle on dev machines ─────────────────────────
        if not prod_mode():
            logger.info("Non-Linux environment — exiting after one cycle (dev mode).")
            break

        time.sleep(Config.refresh_rate)

except Exception:
    logger.exception("Unexpected error in desk allocator loop")

finally:
    # Always notify Slack on exit so the team knows allocator has stopped
    slack.send_message(channel=Config.channel_id, text=Config.shutdown_message)
    logger.info("Shutdown notice sent to Slack.")