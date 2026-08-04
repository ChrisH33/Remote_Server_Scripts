"""
config.py
---------
Loads, validates, and exposes configuration for the Desk Allocator.
All environment validation runs on import so the script fails fast before
any network or API calls are made.
"""

# std modules
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

# Add parent directory to path for universal imports
sys.path.append(str(Path(__file__).parent.parent.resolve()))

# universal imports
from utils.config import logger, require_env

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN = require_env("SLACK_BOT_TOKEN")
CHANNEL_ID      = require_env("SLACK_CHANNEL_DeskAllocator")  # You'll need to add this to .env
SPREADSHEET_ID  = require_env("DESK_ALLOCATOR_SHEET_ID")      # You'll need to add this to .env
SHEET_NAME      = require_env("DESK_ALLOCATOR_SHEET_NAME")    # e.g., "Sheet1" or "Desk Assignments"

# ---------------------------------------------------------------------------
# Local credential files (reusing Google Drive credentials)
# ---------------------------------------------------------------------------

BASE_DIR         = Path(__file__).parent.parent.resolve()
CREDENTIALS_FILE = BASE_DIR / "googledrive_upload" / "credentials.json"
TOKEN_FILE       = BASE_DIR / "googledrive_upload" / "token.json"

# Verify credentials exist
if not CREDENTIALS_FILE.exists():
    raise RuntimeError(
        f"Google credentials file not found: {CREDENTIALS_FILE}\n"
        f"Please ensure credentials.json exists in googledrive_upload/"
    )

if not TOKEN_FILE.exists():
    logger.warning(
        f"Google token file not found: {TOKEN_FILE}\n"
        f"OAuth flow will run on first execution."
    )

# ---------------------------------------------------------------------------
# Scopes for Google Sheets API
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

logger.info("Environment validation successful")

# ---------------------------------------------------------------------------
# Config dataclass  (frozen = immutable after construction)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Config:
    # Google Sheets
    spreadsheet_id: str
    sheet_name:     str
    credentials:    Path
    google_token:   Path
    scopes:         List[str]

    # Slack
    slack_bot_token: str
    channel_id:      str

    # Timing
    refresh_rate: int   # seconds between sheet checks

    # Messages
    startup_message:  str
    shutdown_message: str


def load_var() -> Config:
    return Config(
        spreadsheet_id=SPREADSHEET_ID,
        sheet_name=SHEET_NAME,
        credentials=CREDENTIALS_FILE,
        google_token=TOKEN_FILE,
        scopes=SCOPES,
        slack_bot_token=SLACK_BOT_TOKEN,
        channel_id=CHANNEL_ID,
        refresh_rate=300,  # Check every 5 minutes (adjust as needed)
        startup_message="🟢 Desk Allocator online",
        shutdown_message="🔴 Desk Allocator offline",
    )