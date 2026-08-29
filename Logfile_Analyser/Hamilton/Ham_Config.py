import re

# =========================================================================
# STEPS TO RUN - flip any of these to False to skip that step
# =========================================================================

STEPS_TO_RUN = {
    "parse_logs":           True,   # Condense traces into a single .csv
    "clean_logs":           False,   # Tidy raw csv into a Tableau-ready csv
    "create_log_hyper":     False,   # Convert tidy csv into a hyper file
    "create_util":          False,   # Create a utilisation report
    "create_util_hyper":    False,   # Convert tidy csv into a hyper file
    "publish_hypers":       False,   # Push hyper file to Tableau server
    "check_stale":          False,   # Create a warning if an instrument has gone quiet for too long
    "send_slack":           False,   # Send an update to Slack informing users of run success
}

# =========================================================================
# CONFIG - the settings you're most likely to want to change
# =========================================================================

FILE_EXTENSION = "*.trc"
METHOD_RE = re.compile(r"system : analyze method - start; method file .*\\([^\\]+)\.hsl",re.IGNORECASE,)
SERIAL_RE = re.compile(r"serial number of instrument:\s*(\S+)", re.IGNORECASE)

START_PATTERNS = {
    "start":            "system : start method - complete;",
}

END_PATTERNS = {
    "end_1":            "system : end method - start;",
    "end_2":            "system : custom dialog - start; <method finished>",
    "end_3":            "system : custom dialog - start; <protocol complete>",
    "end_4":            "user : trace - complete; clean up completed",
    "end_5":            "available button(s): <ok>,   default button: <ok>,   message: <end of uv decontamination process.>",
    "end_6":            "microlab® star : end method command - start;",
    "abort_1":          "system : abort method - start;",
    "abort_2":          "system : method has been aborted by the user - complete;",
    "abort_3":          "system : method has been aborted by the method - complete;",
    "abort_4":          "system : execute method - error; an error occurred while running vector.",
}