"""
file_parser.py
--------------
Parses instrument-state update files dropped onto the network share.

Each file is a two-row CSV (header + one data row) with columns:
    instrument, state, method, method_start_time, user

The file's mtime is also captured as `file_creation_time`.
"""

# std modules
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

# universal imports
from utils.config import logger


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# Keeps the rest of the code readable without a full dataclass
UpdateFields = Dict[str, str]

_EXPECTED_KEYS = [
    "instrument",
    "state",
    "method",
    "method_start_time",
    "user",
]

_DEFAULTS: UpdateFields = {
    "instrument":         "Unknown",
    "state":              "Unknown",
    "method":             "Unknown",
    "method_start_time":  "Unknown",
    "user":               "Unknown",
    "file_creation_time": "Unknown",
}


# ---------------------------------------------------------------------------
# Main Function
# ---------------------------------------------------------------------------

def parse_update(file_path: Path | str) -> UpdateFields:
    """
    Parse a single instrument-state update file.

    Returns a dict with keys: instrument, state, method, method_start_time,
    user, file_creation_time.  Any missing values fall back to "Unknown".
    """
    fields = dict(_DEFAULTS)

    # Capture the file modification time as a proxy for when the update was written
    try:
        created_ts = os.path.getmtime(file_path)
        fields["file_creation_time"] = datetime.fromtimestamp(created_ts).isoformat()
    except OSError as e:
        logger.warning(f"Could not read mtime for {file_path}: {e}")

    try:
        with open(file_path, "r", newline="") as fh:
            reader = csv.reader(fh)
            next(reader, None)   # skip header row
            row = next(reader, None)

            if row is None:
                logger.error(f"Update file is empty: {file_path}")
                return fields

            for i, value in enumerate(row):
                if i < len(_EXPECTED_KEYS):
                    fields[_EXPECTED_KEYS[i]] = value

            if len(row) > len(_EXPECTED_KEYS):
                logger.warning(
                    f"Extra columns in {file_path} will be ignored "
                    f"({len(row)} found, {len(_EXPECTED_KEYS)} expected)"
                )

    except Exception as e:
        logger.error(f"Failed to parse update file {file_path}: {e}")

    return fields
