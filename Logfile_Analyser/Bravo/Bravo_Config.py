from pathlib import Path

LOG_FOLDER = Path(r"\\file01-s0\0.051 Research & Development\Instrumentation\Logfiles\Bravo")  # <-- Logfile location
LOG_FOLDER = Path(r"W:\0.051 Research & Development\Instrumentation\Logfiles\Bravo")  # <-- Logfile location
LOG_FOLDER = Path(r"C:\Users\ch33\Documents\Bravo")


PROCESSED_FOLDER = LOG_FOLDER / "Processed"
MOVE_FILES_AFTER_PARSE = True

OUTPUT_FILE = LOG_FOLDER / "CondensedLogs_Raw.csv" 
TIDY_OUTPUT_FILE = LOG_FOLDER / "TidyLogs_ForTableau.csv"
TABLEAU_FILE = LOG_FOLDER / "TidyLogs.hyper"

TRACE_FOLDER = LOG_FOLDER / "Traces"
PYTHON_LOG_FILE = TRACE_FOLDER / "python_logs.txt"
STALE_INSTRUMENTS = TRACE_FOLDER / "stale_instruments.txt"

TABLEAU_SERVER_ADDRESS = "https://globalreporting.internal.sanger.ac.uk"
TABLEAU_SITE_ID = ""
TABLEAU_PROJECT_ID = "0c88cccd-6f5c-4cd5-9641-f01c10fdbc3e"
TABLEAU_DATA_NAME = "Bravo Tidy Logs"

DAYS_BEFORE_STALE = 45

# =========================================================================
# STEPS TO RUN - flip any of these to False to skip that step
# =========================================================================

STEPS_TO_RUN = {
    "parse_logs":   True,   # Condense traces into a single .csv
    "clean_logs":   True,   # Tidy raw csv into a Tableau-ready csv
    "create_hyper": True,   # Convert tidy csv into a hyper file
    "publish":      True,   # Push hyper file to Tableau server
    "check_stale":  True,   # Create a warning if an instrument has gone quiet for too long
}

# =========================================================================
# CONFIG - the settings you're most likely to want to change
# =========================================================================

STATUSES_TO_DROP = {
    "Read Error",
    "No Start Found"
}

FILENAME_PREFIXES_TO_DROP = (
    "HxUsbComm",
    "ComTrace_Simulator",
    "Hamilton Backup Utility",
    "hamilton backup utility"
)

PIPELINE_CODES = {
    "ISC",
    "LCMB",
    "WGS",
    "10X",
    "Ultima"
}

FIELDS = [
    ("instrument",  "Instrument"),
    ("filename",    "Filename"),
    ("start_time",  "Start Time"),
    ("end_time",    "End Time"),
    ("status",      "Status"),
    ("sim_mode",    "Sim Mode"),
    ("method",      "Method"),
    ("tips_96MPH",  "tips 96MPH"),
    ("tips_384MPH", "tips 384MPH"),
]

TIDY_FIELDS = [
    ("instrument", "Instrument", "text"),
    ("filename", "Filename", "text"),
    ("start_time", "Start Time", "datetime"),
    ("end_time", "End Time", "datetime"),
    ("status", "Status", "text"),
    ("sim_mode", "Sim Mode", "text"),
    ("method", "Method", "text"),
    ("tips_96MPH", "Tips 96MPH", "int"),
    ("tips_384MPH", "Tips 384MPH", "int"),
    ("run_duration_minutes", "Run Duration (min)", "float"),
    ("run_date", "Run Date", "date"),
    ("pipeline", "Pipeline", "text"),
    ("process_type", "Process Type", "text"),
    ("method_simplified", "Method Simp.", "text")
]