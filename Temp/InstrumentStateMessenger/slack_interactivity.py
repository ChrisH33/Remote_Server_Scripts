# stdlib
import os
import csv
import sys
import random
import time
from datetime import datetime
from pathlib import Path

# third-party

# internal
from config import load_var, logger
import slack_block_builder

# shared ubuntu scripts
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))
import UniFunction
from SlackClientWrapper.slack_client_wrapper.slack_wrapper import SlackClientWrapper


# =================================================================
# Set Config & Slack
# =================================================================

config = load_var()
slack_wrapper = SlackClientWrapper(bot_token=config.slack_bot_token)

# =================================================================
# Slack Actions
# =================================================================

# Define action event listener
@slack_wrapper.action("Button1")
@slack_wrapper.action("Button2")
@slack_wrapper.action("Button3")
def handle_button_click(ack, body):
    # Acknowledge the message from Slack
    try:
        ack()
    except Exception as e:
        logger.error(f"Failed to acknowledge message from Slack: {e}")
        return  # Early exit if acknowledgment fails