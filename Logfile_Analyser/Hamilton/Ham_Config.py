import re

# =========================================================================
# STEPS TO RUN - flip any of these to False to skip that step
# =========================================================================

STEPS_TO_RUN = {
    "parse_logs":           True,   # Condense traces into a single .csv
    "clean_logs":           True,   # Tidy raw csv into a Tableau-ready csv
    "create_log_hyper":     True,   # Convert tidy csv into a hyper file
    "create_util":          True,   # Create a utilisation report
    "create_util_hyper":    True,   # Convert tidy csv into a hyper file
    "publish_hypers":       True,   # Push hyper file to Tableau server
    "check_stale":          True,   # Create a warning if an instrument has gone quiet for too long
    "send_slack":           True,   # Send an update to Slack informing users of run success
}

# =========================================================================
# CONFIG - the settings you're most likely to want to change
# =========================================================================

FILE_EXTENSION = "*.trc"
METHOD_RE = re.compile(r"method file .*\\([^\\]+)\.hsl",re.IGNORECASE,)
SERIAL_RE = re.compile(r"serial number of instrument:\s*(\S+)", re.IGNORECASE)

FILENAME_PREFIXES_TO_DROP = (
    "HxUsbComm",
    "ComTrace_Simulator",
    "Hamilton Backup Utility",
    "BioMedInstrument",
)
STATUSES_TO_DROP = {
    "Read Error",
    "No Start Found"
}
PATTERNS = {
    "Method Name":      "system : analyze method - start; method file",
    "serial":           "star : start method command - progress; serial number of instrument:",
    "start":            "system : start method - complete;",
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
ABORT_PATTERNS = (
    "abort_1",
    "abort_2",
    "abort_3",
    "abort_4",
)
END_PATTERNS = (
    "end_1",
    "end_2",
    "end_3",
    "end_4",
    "end_5",
    "end_6",
    "abort_1",
    "abort_2",
    "abort_3",
    "abort_4",
)