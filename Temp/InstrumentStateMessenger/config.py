import sys
import platform
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))
from UniFunction import require_env, logger, dir_exists

# -------------------------------------------------
# Environmental Variables
# -------------------------------------------------

load_dotenv()
SLACK_BOT_TOKEN = require_env("SLACK_BOT_TOKEN")
CHANNEL_ID = require_env("SLACK_CHANNEL_InstrumentUpdates")

# -------------------------------------------------
# Platform-specific paths
# -------------------------------------------------

LINUX_PREFIX = Path("/mnt/dna_pipelines")
WINDOWS_PREFIX = Path("W:/")
DNAP_SUBDIR = Path()
BASE_PREFIX = LINUX_PREFIX if platform.system() == "Linux" else WINDOWS_PREFIX
NETWORK_DIR = BASE_PREFIX / DNAP_SUBDIR
NETWORK_DIR = Path("C:/Users/ch33/Documents/Chris")
# -------------------------------------------------
# Validation (runs on import)
# -------------------------------------------------

logger.info("Validating environment...")

dir_exists(NETWORK_DIR, "Network working directory")

logger.info("Environment validation successful")

# -------------------------------------------------
# Config object
# -------------------------------------------------

@dataclass(frozen=True)
class Config:
    refresh_rate: float
    network_dir: str
    slack_bot_token: str
    slack_channel: str

# -------------------------------------------------
# Public API
# -------------------------------------------------

def load_var() -> Config:
    return Config(
        refresh_rate=15,
        network_dir=NETWORK_DIR,
        slack_bot_token=SLACK_BOT_TOKEN,
        slack_channel=CHANNEL_ID
    )