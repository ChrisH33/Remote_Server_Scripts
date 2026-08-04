"""
config.py
---------
Loads, validates, and exposes configuration for the Google Drive uploader.
All environment validation runs on import so the script fails fast before
any network or API calls are made.
"""

# std modules
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import List

# universal imports
from utils.config import dir_exists, file_exists, logger, require_env

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN = require_env("SLACK_BOT_TOKEN")
CHANNEL_ID      = require_env("SLACK_CHANNEL_RemoteLog")
SCOPES          = require_env("SCOPES").split(",")
FOLDER_ID       = require_env("MAVE_DRIVE_FOLDER_ID")

# ---------------------------------------------------------------------------
# Platform-specific paths
# ---------------------------------------------------------------------------

LINUX_PREFIX   = Path("/mnt/dna_pipelines")
WINDOWS_PREFIX = Path("W:/")

DNAP_NETWORK_SUBDIR = Path(
    "0.253 Short Read (SR)"
    "/1. Short Read Library creation"
    "/8. MAVE_SGE"
    "/SGE Upload"
)

BASE_PREFIX   = LINUX_PREFIX if platform.system() == "Linux" else WINDOWS_PREFIX
NETWORK_DIR   = BASE_PREFIX / DNAP_NETWORK_SUBDIR
PROCESSED_DIR = NETWORK_DIR / "Processed"

# ---------------------------------------------------------------------------
# Local credential files
# ---------------------------------------------------------------------------

BASE_DIR         = Path(__file__).parent.resolve()
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE       = BASE_DIR / "token.json"

# credentials.json must exist
file_exists(CREDENTIALS_FILE, "Google credentials file")

#  token.json must exist
if TOKEN_FILE.exists():
    file_exists(TOKEN_FILE, "Google token file")

# ---------------------------------------------------------------------------
# Directory validation  (runs on import — fails fast before any API calls)
# ---------------------------------------------------------------------------

logger.info("Validating environment...")

dir_exists(BASE_PREFIX, "Base network mount")
dir_exists(NETWORK_DIR, "Network working directory")

try:
    PROCESSED_DIR.mkdir(exist_ok=True)
except PermissionError as e:
    raise RuntimeError(
        f"No permission to create Processed directory: {PROCESSED_DIR}"
    ) from e

logger.info("Environment validation successful")

# ---------------------------------------------------------------------------
# Config dataclass  (frozen = immutable after construction)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Config:
    # Paths
    network_dir:           Path
    processed_network_dir: Path
    credentials:           Path
    google_token:          Path

    # Google Drive
    scopes:        List[str]
    mave_folder_id: str

    # Slack
    slack_bot_token: str
    channel_id:      str

    # Timing
    refresh_rate: int   # seconds between directory scans

    # Startup / shutdown messages
    startup_message:  str
    shutdown_message: str


def load_var() -> Config:
    return Config(
        network_dir=NETWORK_DIR,
        processed_network_dir=PROCESSED_DIR,
        credentials=CREDENTIALS_FILE,
        google_token=TOKEN_FILE,
        scopes=SCOPES,
        mave_folder_id=FOLDER_ID,
        slack_bot_token=SLACK_BOT_TOKEN,
        channel_id=CHANNEL_ID,
        refresh_rate=15,
        startup_message="🟢 Drive uploader online",
        shutdown_message="🔴 Drive uploader offline",
    )