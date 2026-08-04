from config import active_block_state, script_history, block_start_time
from datetime import datetime, timezone

def build_status_bar(blocks, max_blocks, emoji_map):
    padded_blocks = blocks.copy()
    while len(padded_blocks) < max_blocks:
        padded_blocks.insert(0, "grey")
    return "".join([emoji_map.get(status, emoji_map["grey"]) for status in padded_blocks])

def rollover_blocks(status_bar, max_blocks):
    while len(status_bar) > max_blocks:
        status_bar.pop(0)  # remove oldest block
    return status_bar
            
def build_slack_blocks(header, max, emojis):
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"{header}",
            "emoji": True
        }})
    
    # Scripts Section
    for script, block_list in script_history.items():
        status_bar = build_status_bar(active_block_state.get(script, block_list), max, emojis)
        blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{script}*\n{status_bar}"
        }})

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

def update_live_status(scripts, cycle_time):
    """
    Update the active_block_state for scripts currently running.
    Adds:
      - green blocks every CYCLE_TIME while active
      - red blocks when scripts disappear
      - orange blocks when scripts return after a disappearance
    """
    now = datetime.now(timezone.utc)

    # New or active scripts
    for script in scripts:
        if script not in script_history:
            script_history[script] = []
            active_block_state[script] = []
            block_start_time[script] = now

        # Add a green block if enough time (CYCLE_TIME) has passed
        last_time = block_start_time.get(script, now - cycle_time)
        if not active_block_state[script] or (now - last_time) >= cycle_time:
            active_block_state[script].append("green")
            block_start_time[script] = now

    # Scripts that vanished
    for script in script_history.keys():
        if script not in scripts:
            last_status = active_block_state.get(script, [])[-1:]
            if not last_status or last_status[0] != "red":
                active_block_state.setdefault(script, []).append("red")
                block_start_time[script] = now

    # Scripts that returned after vanish
    for script in scripts:
        last_status = active_block_state.get(script, [])[-1:]
        if last_status and last_status[0] == "red":
            active_block_state[script][-1] = "orange"
            block_start_time[script] = now
