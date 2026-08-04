"""
slack_messager.py
-----------------
Entry point for the Remote Monitor.

Lifecycle
---------
1.  Post the initial (empty) dashboard to Slack and capture its timestamp.
2.  Loop every `refresh_rate` seconds:
      a. Scan running Python processes.
      b. Update in-memory green/red state.
      c. Trim oldest entries if over the display limit.
      d. Push the updated Block Kit payload to the same Slack message.
3.  On clean exit (SIGTERM, SIGINT, or dev-mode break) update the dashboard
    to show the monitor is offline so the team knows the data is stale.

Dev / non-Linux behaviour
--------------------------
On non-Linux machines `prod_mode()` returns False and the loop runs exactly
once.  This lets you test locally without an infinite loop — just run the
script and inspect the Slack message.
"""

# std modules
import signal
import sys
import time
from dotenv import load_dotenv
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.resolve()))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# universal modules
from utils.config import prod_mode, logger
from utils.slack_wrapper import SlackClientWrapper

# local modules
from config import load_var
from message_builder import build_slack_blocks, update_live_status
from process_scan import get_active_scripts_with_runtime

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

# ── Post initial dashboard — bail out if this fails ──────────────────
blocks = build_slack_blocks(Config.status_header,Config.max_blocks, Config.emoji_map)
ts = None
for attempt in range(1, 4):
    ts = slack.send_message(
        channel=Config.channel_id,
        text="temp",
        blocks=blocks,
    )
    if ts:
        logger.info(f"Dashboard posted (ts={ts})")
        break
    logger.warning(f"Initial post attempt {attempt}/3 failed — retrying in 5s")
    time.sleep(5)

if not ts:
    logger.error("Could not post initial dashboard after all retries — exiting.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

try:
    while not _shutdown_requested:
        active_scripts = get_active_scripts_with_runtime(Config.keywords)

        update_live_status(active_scripts, Config.max_blocks, Config.cycle_time)

        blocks = build_slack_blocks(Config.status_header, Config.max_blocks, Config.emoji_map)
        slack.update_message(
            message_ts=ts,
            channel=Config.channel_id,
            text="Remote monitor",
            blocks=blocks,
        )
        
        time.sleep(Config.refresh_rate)
        if not prod_mode():
            logger.info("Non-Linux environment — exiting after one cycle (dev mode).")
            break
except Exception:
    logger.exception("Unexpected error in monitoring loop")
finally:
    # Always mark the dashboard offline on exit so the team knows data is stale
    slack.update_message(
        message_ts=ts,
        channel=Config.channel_id,
        text="temp",
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": Config.status_header, "emoji": True},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": ":red_circle: *Monitor offline* — data is stale"},
            },
        ],
    )
    logger.info("Dashboard updated to offline state.")