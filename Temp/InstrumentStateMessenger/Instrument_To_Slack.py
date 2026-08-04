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
# Functions
# =================================================================

def parse_update(file_path):
    fields = {
        "instrument": "Unknown",
        "state": "Unknown",
        "method": "Unknown",
        "method_start_time": "Unknown",
        "user": "Unknown",
        "file_creation_time": "Unknown"
    }

    # File creation time
    created_ts = os.path.getmtime(file_path)
    fields["file_creation_time"] = datetime.fromtimestamp(created_ts).isoformat()

    with open(file_path, 'r', newline='') as file:
        reader = csv.reader(file)
        next(reader, None)
        row = next(reader, None)
        if row is None:
            logger.error("CSV update file is empty")
            return fields
        
        # Map row values to dictionary keys 
        keys = [
            "instrument",
            "state",
            "method",
            "method_start_time",
            "user",
        ]      
        for i, value in enumerate(row):
            if i < len(keys):
                fields[keys[i]] = value

        if len(row) > len(keys):
            logger.warning("Extra values in CSV row are being ignored.")

    return fields

def get_random_choice(mapping, key):
    state = (key or "").strip().lower()
    inner = mapping.get(state, {})
    if inner:
        return random.choice(list(inner.values()))
    return None

# =================================================================
# Set Config & Slack
# =================================================================

config = load_var()
slack_wrapper = SlackClientWrapper(bot_token=config.slack_bot_token)

# =================================================================
# Main monitoring loop
# =================================================================

while True:
    # Initial pause between loops
    # time.sleep(config.refresh_rate)

    # Find any available updates
    files = list(config.network_dir.glob("*.txt"))
    if not files:
        continue

    # Pull data from the update
    for file_path in files:
        file_info = parse_update(file_path)

        # # Remove historic Slack updates
        slack_wrapper.delete_specific_messages(
            channel=config.slack_channel,
            match_text=file_info.get("instrument"),
        )

        formatted_time = slack_block_builder.time_format(file_info.get("file_creation_time"))
        image = get_random_choice(slack_block_builder.image_urls, file_info.get("state") or "")
        button1 = get_random_choice(slack_block_builder.slack_buttons["positive"], "ack") or "Acknowledge"
        button2 = get_random_choice(slack_block_builder.slack_buttons["negative"], "stop") or "Stop Run"
        method = file_info.get("method")

        blocks = slack_block_builder.create_slack_message(
            header=":smiley_face:",
            instrument=file_info.get("instrument"),
            status=file_info.get("state"),
            method=method,
            when=formatted_time,
            image=image,
            button_1=button1,
            button_2=button2
        )

        # Send Slack update
        slack_wrapper.send_message(
            channel=config.CHANNEL_ID,
            text="temp text",
            blocks=blocks
        )
    
    # Delete updates
    for file in files:
        os.remove(file)