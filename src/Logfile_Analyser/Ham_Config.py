from pathlib import Path

LOG_FOLDER = Path(r"\\file01-s0\0.051 Research & Development\Instrumentation\Logfiles\Hamilton")  # <-- Logfile location
LOG_FOLDER = Path(r"W:\0.051 Research & Development\Instrumentation\Logfiles\Hamilton")  # <-- Logfile location
# LOG_FOLDER = Path(r"C:\Users\ch33\Documents\Hamilton LogFiles")

DAYS_BEFORE_STALE = 45

PROCESSED_FOLDER = LOG_FOLDER / "Processed"

TIDY_OUTPUT_FILE = LOG_FOLDER / "TidyLogs_ForTableau.csv"

TRACE_FOLDER = LOG_FOLDER / "Traces"
PYTHON_LOG_FILE = TRACE_FOLDER / "python_logs.txt"
STALE_INSTRUMENTS = TRACE_FOLDER / "stale_instruments.txt"