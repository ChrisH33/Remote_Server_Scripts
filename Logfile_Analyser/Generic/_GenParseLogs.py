import re
import os
import csv
import shutil
from typing import List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
import Logfile_Analyser.Main_Config as config
 
# =========================================================================
# Bravo Definitions
# =========================================================================
 
BRAVO_METHOD_RE = re.compile(r"method file: ([^\\]+)\.pro", re.IGNORECASE)
BRAVO_SERIAL_RE = re.compile(r"(Bravo\s*-\s*\d+)", re.IGNORECASE)
 
# =========================================================================
# Hamilton Definitions
# =========================================================================

METHOD_RE = re.compile(r"system : analyze method - start; method file .*\\([^\\]+)\.hsl",re.IGNORECASE,)
SERIAL_RE = re.compile(r"serial number of instrument:\s*(\S+)", re.IGNORECASE)

# =========================================================================
# General Definitions - VARIABLE
# =========================================================================
 
FILE_EXTENSIONS = (
    "*.log",
    "*.trc",
)
START_PATTERNS = {
    "run_start":        "main protocol starting",
    "start":            "system : start method - complete;",
}
END_PATTERNS = {
    "end_1":            "system : end method - start;",
    "end_2":            "system : custom dialog - start; <method finished>",
    "end_3":            "system : custom dialog - start; <protocol complete>",
    "end_4":            "user : trace - complete; clean up completed",
    "end_5":            "available button(s): <ok>,   default button: <ok>,   message: <end of uv decontamination process.>",
    "end_6":            "main protocol complete",
    "abort_1":          "system : abort method - start;",
    "abort_2":          "system : method has been aborted by the;",
    "abort_3":          "main protocol aborted",
    "abort_4":          "system : execute method - error; an error occurred while running vector.",
}
DATETIME_FORMATS = (
    "%d-%b-%y %I:%M:%S %p",
    "%d-%m-%y %I:%M:%S %p",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %I:%M:%S %p",
    "%Y-%m-%d %H:%M:%S",
)
# Best-effort regex used to pull a timestamp-looking chunk out of a line
# before trying to strptime it, since log lines are rarely *just* a timestamp.
TIMESTAMP_RE = re.compile(
    r"\d{1,4}[-/][A-Za-z0-9]{1,4}[-/]\d{2,4}[ ,]+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?",
    re.IGNORECASE,
)
STATUSES_TO_DROP = {
    "Read Error",
    "No Start Found",
}
FILENAME_PREFIXES_TO_DROP = (
    "vworks_log",
    "vworks_time_constraints_log",
    "HxUsbComm",
    "ComTrace_Simulator",
    "Hamilton Backup Utility",
    "BioMedInstrument",
)

# =========================================================================
# General Definitions - FIXED
# =========================================================================
 
@dataclass
class MethodRun:
    instrument: Optional[str] = None
    filename: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "Incomplete"
    sim_mode: Optional[str] = None
    method: Optional[str] = None
    run_duration_minutes: Optional[float] = None
    run_date: Optional[str] = None
    process_type: Optional[str] = None
    method_simplified: Optional[str] = None
 
CSV_FIELDS = [
    ("instrument",              "Instrument",           "text"),
    ("filename",                "Filename",             "text"),
    ("start_time",              "Start Time",           "datetime"),
    ("end_time",                "End Time",             "datetime"),
    ("status",                  "Status",               "text"),
    ("sim_mode",                "Sim Mode",             "text"),
    ("method",                  "Method",               "text"),
    ("run_duration_minutes",    "Run Duration (min)",   "float"),
    ("run_date",                "Run Date",             "date"),
    ("process_type",            "Process Type",         "text"),
    ("method_simplified",       "Method Simp.",         "text"),
]
MAX_WORKERS = min(8, os.cpu_count() or 8)  # currently unused; parsing is sequential
move_files = config.MOVE_FILES_AFTER_PARSE
process_types = config.PROCESS_TYPES
 
# =========================================================================
# Basic Functions
# =========================================================================
 
def parse_timestamp(line: str) -> Optional[datetime]:
    """Try to pull a timestamp out of a log line and parse it."""
    if not line:
        return None
    line = str(line).strip()
    if not line:
        return None

def parse_method_name(line: str):
    match = METHOD_RE.search(line)
    if match:
        return match.group(1)
    return None

def parse_status(line: str):
    for key, pattern in END_PATTERNS.items():
        if pattern in line:
            return "Complete" if key.lower() == "complete" else "Aborted"
    return None

def parse_simulation_mode(line: str):
    match = SERIAL_RE.search(line)
    if match:
        serial = match.group(1).strip()
        return "Sim" if serial == "0000" else "Live"
    return None

# =========================================================================
# Complex Functions
# =========================================================================

def find_logfiles(
    log_folder: Path, 
    processed_folder: Path,
) -> list[Path]:
    
    files = List[Path] = []
    skipped_count = 0
    ignored = {processed_folder.resolve()}
    lowered_prefixes = tuple(prefix.lower() for prefix in files_to_drop)

    for entry in log_folder.iterdir():
        if not entry.is_dir() or entry.resolve() in ignored:
            continue

        for logfile in entry.rglob(FILE_EXTENSION):
            if logfile.name.lower().startswith(lowered_prefixes):
                skipped_count += 1
                continue
            files.append(logfile)
    return files, skipped_count

def calculate_fields(
    raw_row: dict,
    csv_fields: list[tuple[str, str, str]],
    process_types: dict,
    date_formats,
) -> list:

    start_time = parse_timestamps(raw_row.get("Start Time", ""), date_formats)
    end_time = parse_timestamps(raw_row.get("End Time", ""), date_formats)
    method = raw_row.get("Method", "")
    run_duration = round(((end_time - start_time).total_seconds() / 60), 2)if start_time and end_time else None
    run_date = start_time.date().isoformat() if start_time else None

    for process_type, simplified_methods in process_types.items():
        for method_simplified, variants in simplified_methods.items():
            if any(v.casefold() == method.casefold() for v in variants):
                break

    data = {
        "instrument": raw_row.get("Instrument", ""),
        "filename": raw_row.get("Filename", ""),
        "start_time": start_time,
        "end_time": end_time,
        "status": raw_row.get("Status", ""),
        "sim_mode": raw_row.get("Sim Mode", ""),
        "method": method,
        "run_duration_minutes": run_duration,
        "run_date": run_date,
        "process_type": process_type,
        "method_simplified": method_simplified,
    }
    return [data.get(key,"") for key, _, _ in csv_fields]

def write_results(
    rows: list[list],
    output_file: Path,
    fields: list[tuple[str, str, str]]
) -> None:
    """Write all parsed results to the CSV."""
    with output_file.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # If creating the file, add the headers
        if output_file.stat().st_size == 0:
            writer.writerow([display_name for _, display_name, _ in fields])

        # Add the data
        writer.writerows(rows)

def process_file(logfile: Path):
    """Parse one logfile and return its path and extracted data."""
    runs = []
    current_run = None
    last_line = None

    with logfile.open("r", encoding="utf-8", errors="ignore") as file:
        for raw_line in file:
            line = raw_line.rstrip("\n")
            last_line = line
            line_lower = line.lower()

            # ---------------------------------------------------------
            # New run detected
            # ---------------------------------------------------------
            if any(i in line_lower for i in START_PATTERNS.values()):
                current_run = BravoRun()
                current_run.instrument = logfile.parent.name
                current_run.start_time = parse_timestamp(line)

                method = parse_method_name(line)
                if method:
                    current_run.method = method

            # Ignore pre-run information
            if current_run is None:
                continue



            # Method Name
            if current_run.method is None:
                current_run.method = parse_method_name(line)

            # End / abort
            if current_run.start_time is not None:
                if any(i in line_lower for i in END_PATTERNS.values()):
                    current_run.end_time = parse_timestamp(line_lower)
                    current_run.status = parse_status(line_lower)

            # Unique FileID
            if current_run.method and current_run.start_time:
                current_run.uniqueID = (
                    f"{current_run.instrument}_"
                    f"{current_run.start_time:%Y%m%d_%H%M%S}_"
                    f"{current_run.method}"
                )

                runs.append(current_run)
                current_run = None


    # ---------------------------------------------------------
    # End of file fallback
    # ---------------------------------------------------------
    if current_run:
        if current_run.status == "Incomplete":
            current_run.end_time = parse_timestamp(last_line)
        runs.append(current_run)
    
    return runs


# =========================================================================
# MAIN PARSER
# =========================================================================
def run_parser(log_folder: Path, output_file: Path, logger) -> None:

    logger.info("=== Log parser starting ===")

    # ---------------------------------------------------------
    # 1. Find all files
    # ---------------------------------------------------------

    logger.info("Looking for files to process...")

    processed_folder = log_folder.parent / "Processed"
    files, skipped_count = find_logfiles(log_folder, processed_folder)
    total_files = len(files)

    logger.info(
        f"Found {total_files} files "
        f"({skipped_count} skipped by filename filter). "
    )

    # ---------------------------------------------------------
    # 2. Parse every file
    # ---------------------------------------------------------
    
    results = []

    # ---------------------------------------------------------
    # 3. Write all parsed results to CSV
    # ---------------------------------------------------------

    logger.info(f"Writing results to {output_file}")

    for _, raw_row in results:
        tidy_row = calculate_fields(raw_row, csv_fields, process_types, date_formats)

    write_results([tidy_row], output_file, csv_fields)

    # ---------------------------------------------------------
    # 4. Move all parsed files to Processed
    # ---------------------------------------------------------

    logger.info("Moving parsed files to Processed...")

    if move_files:
        for logfile, _ in results:
            instrument_folder = logfile.parent.name
            destination_folder = (processed_folder / instrument_folder)
            destination_folder.mkdir(parents=True, exist_ok=True)
            destination = (destination_folder / logfile.name)
            try:
                shutil.move(str(logfile), str(destination))
            except OSError as e:
                logger.warning(f"Parsed {logfile.name} but could not move it: {e}")
    else:
        logger.info("Skipping logfile transfer")

    logger.info(f"Finished. {len(rows)} results saved to {Path(output_file).name}")