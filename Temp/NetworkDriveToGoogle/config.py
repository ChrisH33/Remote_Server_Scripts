import sys
from pathlib import Path
import platform
import logging
from dataclasses import dataclass
from datetime import timedelta
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.resolve()  # goes up from RemoteScriptTracker/
sys.path.append(str(project_root))
from UniFunction import require_env, logger, dir_exists, file_exists

# -------------------------------------------------
# Environmental Variables
# -------------------------------------------------

load_dotenv()
SLACK_BOT_TOKEN = require_env("SLACK_BOT_TOKEN")
CHANNEL_ID = require_env("SLACK_CHANNEL_RemoteLog")
SCOPES = require_env("SCOPES").split(",")
FOLDER_ID = require_env("MAVE_DRIVE_FOLDER_ID")

# -------------------------------------------------
# Platform-specific paths
# -------------------------------------------------

LINUX_PREFIX = Path("/mnt/dna_pipelines")
WINDOWS_PREFIX = Path("W:/")

DNAP_NETWORK_SUBDIR = Path(
    "0.253 Short Read (SR)"
    "/1. Short Read Library creation"
    "/8. MAVE_SGE"
    "/SGE Upload"
)

BASE_PREFIX = LINUX_PREFIX if platform.system() == "Linux" else WINDOWS_PREFIX
NETWORK_DIR = BASE_PREFIX / DNAP_NETWORK_SUBDIR
PROCESSED_DIR = NETWORK_DIR / "Processed"

# -------------------------------------------------
# Local files
# -------------------------------------------------

BASE_DIR = Path(__file__).parent.resolve()
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

# -------------------------------------------------
# Validation (runs on import)
# -------------------------------------------------

logger.info("Validating environment...")

dir_exists(BASE_PREFIX, "Base network mount")
dir_exists(NETWORK_DIR, "Network working directory")
try:
    PROCESSED_DIR.mkdir(exist_ok=True)
except PermissionError as e:
    raise RuntimeError(
        f"No permission to create Processed directory: {PROCESSED_DIR}"
    ) from e
file_exists(CREDENTIALS_FILE, "Google credentials file")
file_exists(TOKEN_FILE, "Google token file")

logger.info("Environment validation successful")

# -------------------------------------------------
# Config object
# -------------------------------------------------

@dataclass(frozen=True)
class Config:
    refresh_rate: int
    network_dir: Path
    processed_network_dir: Path
    credentials: Path
    google_token: Path
    slack_bot_token: str
    channel_id: str
    scopes: list
    mave_folder_id: str

# -------------------------------------------------
# Public API
# -------------------------------------------------

def load_var() -> Config:
    return Config(
        refresh_rate=15,
        network_dir=NETWORK_DIR,
        processed_network_dir=PROCESSED_DIR,
        credentials=CREDENTIALS_FILE,
        google_token=TOKEN_FILE,
        slack_bot_token=SLACK_BOT_TOKEN,
        channel_id=CHANNEL_ID,
        scopes=SCOPES,
        mave_folder_id=FOLDER_ID
    )