"""
config.py
---------
Loads and exposes configuration for the Remote Monitor.

Shared mutable state (active_block_state, script_history, block_start_time)
also lives here so every module mutates the *same* objects — not local copies.
"""

# std modules
from datetime import timedelta
from dataclasses import dataclass
from typing import Dict, List

# universal imports
from utils.config import require_env

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN = require_env("SLACK_BOT_TOKEN")
CHANNEL_ID      = require_env("SLACK_CHANNEL_RemoteLog")

# ---------------------------------------------------------------------------
# Shared mutable state
# Imported (not copied) by message_builder.py so mutations are visible everywhere.
# ---------------------------------------------------------------------------

active_block_state: dict[str, str]    = {}  # script_name → colour ("green" | "red")
script_history:     dict[str, list]   = {}  # script_name → list[datetime] of start times
block_start_time:   dict[str, object] = {}  # script_name → datetime of last state change

# ---------------------------------------------------------------------------
# Config dataclass  (frozen = immutable after construction)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Config:
    # Slack
    slack_bot_token: str
    channel_id:      str

    # Display
    max_blocks:    int           # max scripts shown in the dashboard at once
    status_header: str           # header text for the Slack Block Kit message
    emoji_map:     Dict[str, str]  # colour string → Slack emoji

    # Timing
    refresh_rate: int            # seconds between Slack updates
    cycle_time:   timedelta      # how long a "red" entry lingers before being removed

    # Process scanning
    keywords: List[str]          # process command-line substrings to ignore


def load_var() -> Config:
    return Config(
        slack_bot_token=SLACK_BOT_TOKEN,
        channel_id=CHANNEL_ID,

        max_blocks=15,
        status_header="Remote Ubuntu Dashboard :skull:",
        emoji_map={
            "green":  ":large_green_square:",   # script is running
            "red":    ":large_red_square:",      # script recently stopped
            "orange": ":large_orange_square:",   # reserved / future use
            "grey":   ":black_large_square:",    # unknown / placeholder
        },

        refresh_rate=20,
        cycle_time=timedelta(minutes=1),

        # Processes whose command lines contain these strings are ignored.
        # Add more here if you see noise (e.g. Jupyter kernels, pytest workers).
        keywords=["launcher", "debugpy", "pythonw.exe"],
    )