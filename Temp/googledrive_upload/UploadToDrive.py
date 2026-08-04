"""
UploadToDrive.py
----------------
Entry point for the Google Drive uploader.

Lifecycle
---------
1.  Authenticate with Google Drive.
2.  Post a Slack startup notice.
3.  Loop every `refresh_rate` seconds:
      a. Scan the network directory for new CSV / PDF files.
      b. Upload each file to the configured Drive folder.
      c. Move successfully uploaded files to the Processed subfolder.
      d. Post a Slack summary for the batch.
4.  On clean exit (SIGTERM, SIGINT, or dev-mode break) post a shutdown
    notice to Slack so the team knows the uploader is no longer running.

Dev / non-Linux behaviour
--------------------------
On non-Linux machines `prod_mode()` returns False and the loop runs exactly
once.  This lets you test locally without an infinite loop.
"""

# std modules
import os
import signal
import sys
import time
from typing import List
from dotenv import load_dotenv
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.resolve()))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# universal imports
from utils.config import logger, prod_mode
from utils.slack_wrapper import SlackClientWrapper

# local imports
from config import load_var
from file_mover import move_to_processed, upload_file_to_google
from build_drive_service import build_drive_service

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
# Initialise config, Slack and Google
# ---------------------------------------------------------------------------

Config = load_var()
slack  = SlackClientWrapper(bot_token=Config.slack_bot_token)
service = build_drive_service(Config)

# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def retry(func, *args, retries: int = 3, delay: float = 1.0, **kwargs):
    """
    Call `func(*args, **kwargs)` up to `retries` times, waiting `delay`
    seconds between attempts.

    Returns the function's return value on success, or False after all
    retries are exhausted.

    The `retries` and `delay` parameters are keyword-only (they sit after
    `*args`) so they can never be accidentally consumed as positional args.
    """
    for attempt in range(1, retries + 1):
        try:
            result = func(*args, **kwargs)
            if result:
                return result
            logger.warning(
                f"Attempt {attempt}/{retries} failed for {func.__name__}: returned falsy"
            )
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{retries} failed for {func.__name__}: {e}")
        if attempt < retries:
            time.sleep(delay)

    logger.error(f"{func.__name__} failed after {retries} attempts")
    return False

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

try:
    while not _shutdown_requested:
        # ── Scan network directory for uploadable files ───────────────────
        try:
            files = [
                f for f in os.listdir(Config.network_dir)
                if f.lower().endswith((".csv", ".pdf"))
            ]
        except Exception:
            logger.exception("Error accessing network directory")
            time.sleep(Config.refresh_rate)
            continue

        # ── Process each file ─────────────────────────────────────────────
        uploaded_files: List[str] = []
        for file_name in files:
            full_path = os.path.join(Config.network_dir, file_name)

            # Upload first; only move to Processed if upload succeeded
            if retry(
                upload_file_to_google,
                full_path, Config.mave_folder_id, service,
                retries=3, delay=2,
            ):
                if retry(
                    move_to_processed,
                    full_path, Config.processed_network_dir,
                    retries=3, delay=1,
                ):
                    uploaded_files.append(file_name)
                else:
                    logger.error(f"Upload succeeded but move to Processed failed: {full_path}")
            else:
                logger.error(f"Failed to upload to Google Drive after retries: {full_path}")

        # ── Slack summary ─────────────────────────────────────────────────
        if uploaded_files:
            slack.send_message(
                channel=Config.channel_id,
                text=(
                    f"Uploaded {len(uploaded_files)} file(s) to Google Drive:\n"
                    + "\n".join(uploaded_files)
                ),
            )

        # ── Break after one cycle on dev machines ─────────────────────────
        if not prod_mode():
            logger.info("Non-Linux environment — exiting after one cycle (dev mode).")
            break

        time.sleep(Config.refresh_rate)

except Exception:
    logger.exception("Unexpected error in upload loop")

finally:
    # Always notify Slack on exit so the team knows uploads have stopped
    slack.send_message(channel=Config.channel_id, text=Config.shutdown_message)
    logger.info("Shutdown notice sent to Slack.")