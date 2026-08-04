#stdlib
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# internal
from config import load_var, active_block_state
from message_builder import build_slack_blocks, update_live_status, rollover_blocks
from process_scan import get_active_scripts

# Shared Ubuntu scripts
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))
import UniFunction
from SlackClientWrapper.slack_client_wrapper.slack_wrapper import SlackClientWrapper

# =================================================================
# Set Config & Slack
# =================================================================

config = load_var()
slack_wrapper = SlackClientWrapper(bot_token=config.slack_bot_token)

# Send started Slack message
blocks = build_slack_blocks(
    config.status_header,
    config.max_blocks,
    config.emoji_map
)
ts = slack_wrapper.send_message(
    channel=config.channel_id,
    text="temp text",
    blocks=blocks
)

# =================================================================
# Main monitoring loop
# =================================================================

while True:
    # 1. Detect active scripts
    currently_active_scripts = get_active_scripts(config.keywords)

    # 2. Update block statuses
    update_live_status(currently_active_scripts, config.cycle_time)
    rollover_blocks(active_block_state, config.max_blocks)

    # 3. Update Slack message
    blocks = build_slack_blocks(
        config.status_header,
        config.max_blocks,
        config.emoji_map
    )
    slack_wrapper.update_message(
        message_ts=ts,
        channel=config.channel_id,
        text="temp text",
        blocks=blocks
    )

    # 4. Break loop (optional)
    if not UniFunction.prod_mode():
        break

    # 5. 'Wait for' timer
    time.sleep(config.refresh_rate)