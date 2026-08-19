import re

# =========================================================================
# STEPS TO RUN - flip any of these to False to skip that step
# =========================================================================

STEPS_TO_RUN = {
    "parse_logs":           True,   # Condense traces into a single .csv
    "clean_logs":           True,   # Tidy raw csv into a Tableau-ready csv
    "create_log_hyper":     True,   # Convert tidy csv into a hyper file
    "create_util":          True,   # Create a utilisation report
    "create_util_hyper":    False,   # Convert tidy csv into a hyper file
    "publish_hypers":       False,   # Push hyper file to Tableau server
    "check_stale":          True,   # Create a warning if an instrument has gone quiet for too long
    "send_slack":           True,   # Send an update to Slack informing users of run success
}

# =========================================================================
# CONFIG - the settings you're most likely to want to change
# =========================================================================

FILE_EXTENSION = "*.log"
SERIAL_RE = re.compile(r"(Bravo\s*-\s*\d+)", re.IGNORECASE)

TIMESTAMP_FORMATS = (
    "%m/%d/%Y %I:%M:%S %p",
    "%d/%m/%Y %H:%M:%S",
)
PATTERNS = {
    "run_start": "startup protocol starting",
    "runset": "starting runset :",
    "protocol_added": "runset manager: added the run",
    "protocol_file": ".pro",
    "complete": "main protocol complete",
    "logout": "logged out",
}
END_PATTERNS = (
    "complete",
)
ABORT_PATTERNS = (
    "logout",
)
STATUSES_TO_DROP = {
    "Read Error",
    "No Start Found"
}
FILENAME_PREFIXES_TO_DROP = (
    "vworks_pipette_log",
)