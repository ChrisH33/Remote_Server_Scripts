"""
config.py
---------
Loads, validates, and exposes configuration for the Instrument State Messager.
All environment validation runs on import so the script fails fast before
any network or API calls are made.
"""

# std modules
import platform
from dataclasses import dataclass
from pathlib import Path

# universal imports
from utils.config import dir_exists, logger, require_env

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

SLACK_BOT_TOKEN = require_env("SLACK_BOT_TOKEN")
CHANNEL_ID      = require_env("SLACK_CHANNEL_InstrumentUpdates")
SLACK_APP_TOKEN = require_env("SLACK_APP_TOKEN")   # required for socket-mode interactivity

# ---------------------------------------------------------------------------
# Platform-specific paths
# ---------------------------------------------------------------------------

LINUX_PREFIX   = Path("/mnt/dna_pipelines")
WINDOWS_PREFIX = Path("W:/")

# TODO: set the subdirectory path beneath the network mount where
# instrument update .txt files are written, e.g.:
#   DNAP_SUBDIR = Path("0.253 Short Read (SR)/Instruments/Updates")
DNAP_SUBDIR = Path("YOUR/SUBDIR/HERE")

BASE_PREFIX = LINUX_PREFIX if platform.system() == "Linux" else WINDOWS_PREFIX
NETWORK_DIR = BASE_PREFIX / DNAP_SUBDIR

# ---------------------------------------------------------------------------
# Directory validation  (runs on import — fails fast before any API calls)
# ---------------------------------------------------------------------------

logger.info("Validating environment...")

dir_exists(NETWORK_DIR, "Network working directory")

logger.info("Environment validation successful")

# ---------------------------------------------------------------------------
# Config dataclass  (frozen = immutable after construction)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Config:
    # Paths
    network_dir: Path

    # Slack
    slack_bot_token: str
    slack_app_token: str   # socket-mode app-level token
    channel_id:      str

    # Timing
    refresh_rate: float   # seconds between directory scans

    # Startup / shutdown messages
    startup_message:  str
    shutdown_message: str


def load_var() -> Config:
    return Config(
        network_dir=NETWORK_DIR,
        slack_bot_token=SLACK_BOT_TOKEN,
        slack_app_token=SLACK_APP_TOKEN,
        channel_id=CHANNEL_ID,
        refresh_rate=15,
        startup_message="🟢 Instrument monitor online",
        shutdown_message="🔴 Instrument monitor offline",
    )
