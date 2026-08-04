# script_status.py
from datetime import datetime, timezone
from shared import logger, script_history, active_block_state, block_start_time, MAX_BLOCKS, CYCLE_TIME

# Emoji map
EMOJI_MAP = {
    "green": ":large_green_square:",
    "red": ":large_red_square:",
    "orange": ":large_orange_square:",
    "grey": ":black_large_square:"
}

def build_status_bar(blocks):
    """
    Convert a list of status strings into a Slack emoji string.
    Pads with grey blocks at the start until length reaches MAX_BLOCKS.
    """
    padded_blocks = blocks.copy()
    while len(padded_blocks) < MAX_BLOCKS:
        padded_blocks.insert(0, "grey")  # add grey to the **front**
    return "".join([EMOJI_MAP.get(status, EMOJI_MAP["grey"]) for status in padded_blocks])

def build_slack_blocks(script_history, active_block_state):
    """
    Return Slack message blocks showing all scripts and their status bars.
    Includes header and last update timestamp.
    """
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "Remote Ubuntu Dashboard :skull:",
            "emoji": True
        }
    })

    # Script sections
    for script, block_list in script_history.items():
        status_bar = build_status_bar(active_block_state.get(script, block_list))
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{script}*\n{status_bar}"
            }
        })

    # Last update
    last_update = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"last update:\n`{last_update}`"
        }
    })

    return blocks

def update_live_status(running_scripts):
    """
    Update the active_block_state for scripts currently running.
    Adds:
      - green blocks every CYCLE_TIME while active
      - red blocks when scripts disappear
      - orange blocks when scripts return after a disappearance
    """
    now = datetime.now(timezone.utc)

    # New or active scripts
    for script in running_scripts:
        if script not in script_history:
            script_history[script] = []
            active_block_state[script] = []
            block_start_time[script] = now

        # Add a green block if enough time (CYCLE_TIME) has passed
        last_time = block_start_time.get(script, now - CYCLE_TIME)
        if not active_block_state[script] or (now - last_time) >= CYCLE_TIME:
            active_block_state[script].append("green")
            block_start_time[script] = now

    # Scripts that vanished
    for script in script_history.keys():
        if script not in running_scripts:
            last_status = active_block_state.get(script, [])[-1:]
            if not last_status or last_status[0] != "red":
                active_block_state.setdefault(script, []).append("red")
                block_start_time[script] = now

    # Scripts that returned after vanish
    for script in running_scripts:
        last_status = active_block_state.get(script, [])[-1:]
        if last_status and last_status[0] == "red":
            active_block_state[script][-1] = "orange"
            block_start_time[script] = now

def rollover_blocks():
    """
    Ensure no script has more than MAX_BLOCKS blocks.
    Removes oldest blocks when over limit.
    """
    for script, blocks in active_block_state.items():
        while len(blocks) > MAX_BLOCKS:
            removed = blocks.pop(0)
            logger.debug(f"Removed oldest block '{removed}' for {script}")