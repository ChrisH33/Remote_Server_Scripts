import os
import logging
from pathlib import Path
import platform

# -------------------------------------------------
# Helpers
# -------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def prod_mode():
    """
    Returns True for Linux-based systems
    """
    if platform.system() == "Linux":
        return True
    else:
        return False

def require_env(name: str) -> str:
    """
    Fetch a required environment variable or fail fast.
    """
    try:
        value = os.environ[name]
        
    except KeyError as e:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set"
        ) from e
    if not value or value.strip().lower() == "none":
        raise RuntimeError(
            f"Environment variable '{name}' is set but empty or None"
        )

    return value.strip()

def dir_exists(path: Path, name: str) -> None:
    """
    Check that a directory exists
    """
    if not path.exists():
        raise RuntimeError(
            f"{name} does not exist: {path}"
        )
    if not path.is_dir():
        raise RuntimeError(
            f"{name} is not a directory: {path}"
        )
    try:
        path.stat()  # forces filesystem access
    except Exception as e:
        raise RuntimeError(
            f"{name} is not accessible: {path}"
        ) from e

def file_exists(path: Path, name: str) -> None:
    if not path.exists():
        raise RuntimeError(
            f"{name} missing: {path}"
        )
    if not path.is_file():
        raise RuntimeError(
            f"{name} is not a file: {path}"
        )
