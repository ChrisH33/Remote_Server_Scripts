"""
instrument_messager.py
----------------------
Entry point for the Instrument State Messager.

Lifecycle
---------
1.  Post a Slack startup notice.
2.  Loop every `refresh_rate` seconds:
      a. Glob the network directory for .txt update files.
      b. For each file: delete the instrument's previous Slack message,
         parse the file, build a new Block Kit message, send it.
      c. Delete files that were successfully sent.
3.  On clean exit (SIGTERM, SIGINT) post a shutdown notice to Slack.

Dev / non-Linux behaviour
--------------------------
On non-Linux machines `prod_mode()` returns False and the loop runs exactly
once.  This lets you test locally without an infinite loop.
"""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path

# universal imports
from utils.config import logger, prod_mode
from utils.slack_wrapper import SlackClientWrapper

# local imports
from config import load_var
from file_parser import parse_update
from message_builder import (
    create_slack_message,
    get_random_choice,
    image_urls,
    slack_buttons,
    time_format,
)

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
# Initialise config and Slack
# ---------------------------------------------------------------------------

Config = load_var()
slack  = SlackClientWrapper(bot_token=Config.slack_bot_token)

slack.send_message(channel=Config.channel_id, text=Config.startup_message)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

try:
    while not _shutdown_requested:
        # ── Find update files ─────────────────────────────────────────────
        files = list(Config.network_dir.glob("*.txt"))

        if not files:
            if not prod_mode():
                logger.info("Non-Linux environment — no files found, exiting (dev mode).")
                break
            time.sleep(Config.refresh_rate)
            continue

        # ── Process each update file ──────────────────────────────────────
        for file_path in files:
            file_info = parse_update(file_path)
            instrument = file_info.get("instrument", "Unknown")

            # Remove any previous Slack message for this instrument so the
            # channel doesn't fill up with stale cards
            slack.delete_specific_messages(
                channel=Config.channel_id,
                match_text=instrument,
            )

            # Build the new Block Kit message
            formatted_time = time_format(file_info.get("file_creation_time"))
            image    = get_random_choice(image_urls,    file_info.get("state") or "")
            button_1 = get_random_choice(slack_buttons["positive"], "ack") or "Acknowledge"
            button_2 = get_random_choice(slack_buttons["negative"], "stop") or "Stop Run"

            blocks = create_slack_message(
                header=":smiley_face:",
                instrument=instrument,
                status=file_info.get("state",  "Unknown"),
                method=file_info.get("method", "Unknown"),
                when=formatted_time,
                image=image,
                button_1=button_1,
                button_2=button_2,
            )

            # Send — only delete the source file if the send succeeded
            ts = slack.send_message(
                channel=Config.channel_id,
                text=f"Instrument update: {instrument}",
                blocks=blocks,
            )

            if ts:
                logger.info(f"Sent update for {instrument}, removing {file_path.name}")
                try:
                    os.remove(file_path)
                except OSError as e:
                    logger.error(f"Could not remove update file {file_path}: {e}")
            else:
                # BUG FIX: original deleted the file even if send failed, losing the update
                logger.error(
                    f"Slack send failed for {instrument} — "
                    f"keeping {file_path.name} for next cycle"
                )

        # ── Break after one cycle on dev machines ─────────────────────────
        if not prod_mode():
            logger.info("Non-Linux environment — exiting after one cycle (dev mode).")
            break

        time.sleep(Config.refresh_rate)

except Exception:
    logger.exception("Unexpected error in instrument monitor loop")

finally:
    # Always notify Slack on exit so the team knows the monitor is down
    slack.send_message(channel=Config.channel_id, text=Config.shutdown_message)
    logger.info("Shutdown notice sent to Slack.")
