from datetime import timedelta
from dataclasses import dataclass
from typing import Dict
from dotenv import load_dotenv
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))
from UniFunction import logger, require_env

# -------------------------------------------------
# Variables
# -------------------------------------------------

active_block_state = {}
script_history = {}
block_start_time = {}

# -------------------------------------------------
# Environmental Variables
# -------------------------------------------------

load_dotenv()
SLACK_BOT_TOKEN = require_env("SLACK_BOT_TOKEN")
CHANNEL_ID = require_env("SLACK_CHANNEL_RemoteLog")

# -------------------------------------------------
# Config object
# -------------------------------------------------

@dataclass(frozen=True)
class Config:
    max_blocks: int
    cycle_time: int
    refresh_rate: int
    keywords: list[str]
    status_header: str
    emoji_map: Dict[str, str]
    slack_bot_token: str
    channel_id: str

# -------------------------------------------------
# Public API
# -------------------------------------------------

def load_var() -> Config:
    return Config(
        max_blocks = 15,
        cycle_time = timedelta(minutes=1),
        refresh_rate = 20,
        keywords = ['launcher', 'debugpy', 'pythonw.exe'],
        status_header = "Remote Ubuntu Dashboard :skull:",
        emoji_map = {
            "green": ":large_green_square:",
            "red": ":large_red_square:",
            "orange": ":large_orange_square:",
            "grey": ":black_large_square:",
        },
        slack_bot_token=SLACK_BOT_TOKEN,
        channel_id=CHANNEL_ID
    )