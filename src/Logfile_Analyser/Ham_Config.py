from pathlib import Path

LOG_FOLDER = Path(r"\\file01-s0\0.051 Research & Development\Instrumentation\Logfiles\Hamilton")  # <-- Logfile location
LOG_FOLDER = Path(r"W:\0.051 Research & Development\Instrumentation\Logfiles\Hamilton")  # <-- Logfile location
# LOG_FOLDER = Path(r"C:\Users\ch33\Documents\Hamilton LogFiles")

PROCESSED_FOLDER = LOG_FOLDER / "Processed"

PYTHON_LOG_FILE = LOG_FOLDER / "python_logs.txt"


TIDY_OUTPUT_FILE = LOG_FOLDER / "TidyLogs_ForTableau.csv"