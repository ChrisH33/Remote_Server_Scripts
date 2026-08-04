"""
slack_interactivity.py
----------------------
Handles interactive button clicks sent back from Slack when a team member
responds to an instrument-state card.

This is a separate long-running process from instrument_messager.py.
It uses Bolt's Socket Mode so no public HTTP endpoint is required — the
app connects outward to Slack's websocket, meaning it works on the same
private network as the rest of the tooling.

Requirements
------------
- SLACK_APP_TOKEN must be set (starts with "xapp-") — enables socket mode.
  Create one at api.slack.com/apps → your app → Socket Mode.
- SLACK_BOT_TOKEN must be set (starts with "xoxb-") — for sending messages.

Button action IDs (must match message_builder.create_slack_message):
  buttonPrimary   — positive acknowledgement ("On my way", "Thanks", etc.)
  buttonSecondary — negative / busy response  ("Can't right now", etc.)
  buttonTertiary  — feedback (reserved)
"""

# std modules
import random
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# universal imports
from utils.config import logger, require_env

# local imports
from message_builder import responses

# ---------------------------------------------------------------------------
# Initialise Bolt app
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN = require_env("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = require_env("SLACK_APP_TOKEN")

app = App(token=SLACK_BOT_TOKEN)


# ---------------------------------------------------------------------------
# Action handlers
# BUG FIX: original used "Button1/2/3" — IDs must match those set in
# message_builder.create_slack_message ("buttonPrimary/Secondary/Tertiary")
# ---------------------------------------------------------------------------

def _post_acknowledgement(body, client, response_key: str) -> None:
    """
    Post a threaded reply acknowledging the button click, crediting the
    user who clicked.
    """
    try:
        user_id  = body["user"]["id"]
        channel  = body["channel"]["id"]
        msg_ts   = body["message"]["ts"]

        response_pool = responses.get(response_key, {})
        action_text   = (
            random.choice(list(response_pool.values()))
            if response_pool
            else "acknowledged"
        )

        client.chat_postMessage(
            channel=channel,
            thread_ts=msg_ts,
            text=f"<@{user_id}> {action_text}",
        )
    except Exception as e:
        logger.error(f"Failed to post acknowledgement reply: {e}")


@app.action("buttonPrimary")
def handle_primary(ack, body, client):
    """Positive acknowledgement — "On my way", "Thanks", etc."""
    try:
        ack()
    except Exception as e:
        logger.error(f"Failed to acknowledge buttonPrimary: {e}")
        return
    _post_acknowledgement(body, client, response_key="positive")


@app.action("buttonSecondary")
def handle_secondary(ack, body, client):
    """Negative / busy response — "Can't right now", etc."""
    try:
        ack()
    except Exception as e:
        logger.error(f"Failed to acknowledge buttonSecondary: {e}")
        return
    # No reply message for the negative button — just acknowledge silently


@app.action("buttonTertiary")
def handle_tertiary(ack, body, client):
    """Feedback button — reserved for future use."""
    try:
        ack()
    except Exception as e:
        logger.error(f"Failed to acknowledge buttonTertiary: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Instrument Interactivity handler (socket mode)...")
    # BUG FIX: original never called start() so the handlers never ran
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
