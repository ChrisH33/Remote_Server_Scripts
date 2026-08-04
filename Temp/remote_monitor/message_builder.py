"""
message_builder.py
------------------
Builds Slack Block Kit payloads and manages per-script colour history.

Each cycle, update_live_status() appends a new colour to every script's
history and shifts the window left by dropping the oldest entry once
the history exceeds max_blocks.

Visual format per script:
    *script_name*  :large_green_square: :large_green_square: :large_red_square:
"""

from datetime import datetime, timedelta
from config import active_block_state, block_start_time, script_history


# ---------------------------------------------------------------------------
# Live-status updater
# ---------------------------------------------------------------------------

def update_live_status(
    currently_active: dict[str, float],
    max_blocks: int,
    cycle_time: timedelta,
) -> None:
    now = datetime.now()
    all_scripts = set(active_block_state.keys()) | set(currently_active.keys())

    for script in all_scripts:
        prev_status = active_block_state.get(script)

        if script in currently_active:
            new_status = "orange" if prev_status == "red" else "green"
            if script not in block_start_time:
                runtime = currently_active[script]
                block_start_time[script] = now - timedelta(seconds=runtime)
        else:
            new_status = "red"

        active_block_state[script] = new_status

        # Prepend newest block on the left, trim oldest on the right
        history = script_history.setdefault(script, [])
        history.insert(0, new_status)
        if len(history) > max_blocks:
            history.pop()


def build_slack_blocks(status_header: str, max_blocks: int, emoji_map: dict) -> list:
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": status_header, "emoji": True},
        },
        {"type": "divider"},
    ]

    if not script_history:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":zzz: No scripts currently running"},
        })
        return blocks

    for script, history in script_history.items():
        # Pad right with grey until we reach max_blocks
        padded = history + ["grey"] * (max_blocks - len(history))
        emoji_str = "".join(emoji_map.get(s, emoji_map["grey"]) for s in padded)

        last_update = block_start_time.get(script)
        ts_str = last_update.strftime("%Y-%m-%d %H:%M:%S") if last_update else "unknown"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{script}*\n{emoji_str}\nstart time: `{ts_str}`",
            },
        })

    return blocks