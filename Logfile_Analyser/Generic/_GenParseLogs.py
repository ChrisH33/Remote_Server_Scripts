import re
import os
import csv
import shutil
from typing import List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
import Logfile_Analyser.Generic._ProcessTypes as config

# =========================================================================
# Bravo Definitions
# =========================================================================

BRAVO_METHOD_RE = re.compile(r"method file: ([^\\]+)\.pro", re.IGNORECASE)
BRAVO_SERIAL_RE = re.compile(r"(Bravo\s*-\s*\d+)", re.IGNORECASE)

# =========================================================================
# Hamilton Definitions
# =========================================================================

HAMILTON_METHOD_RE = re.compile(r"system : analyze method - start; method file .*\\([^\\]+)\.hsl", re.IGNORECASE)
HAMILTON_SERIAL_RE = re.compile(r"serial number of instrument:\s*(\S+)", re.IGNORECASE)

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

    candidates = []
    match = TIMESTAMP_RE.search(line)
    if match:
        candidates.append(match.group(0).strip())
    candidates.append(line)  # fallback: maybe the whole line is a timestamp

    for candidate in candidates:
        for fmt in DATETIME_FORMATS:
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    return None

def parse_method_name(line: str) -> Optional[str]:
    for pattern in (BRAVO_METHOD_RE, HAMILTON_METHOD_RE):
        match = pattern.search(line)
        if match:
            return match.group(1)
    return None

def parse_status(line_lower: str) -> Optional[str]:
    for key, pattern in END_PATTERNS.items():
        if pattern in line_lower:
            return "Complete" if key.startswith("end") else "Aborted"
    return None

def parse_simulation_mode(line: str) -> Optional[str]:
    # Hamilton logs report a serial number; "0000" indicates simulation mode.
    match = HAMILTON_SERIAL_RE.search(line)
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
) -> Tuple[List[Path], int]:

    files: List[Path] = []
    skipped_count = 0
    ignored = {processed_folder.resolve()}
    lowered_prefixes = tuple(prefix.lower() for prefix in FILENAME_PREFIXES_TO_DROP)

    for entry in log_folder.iterdir():
        if not entry.is_dir() or entry.resolve() in ignored:
            continue

        for pattern in FILE_EXTENSIONS:
            for logfile in entry.rglob(pattern):
                if logfile.name.lower().startswith(lowered_prefixes):
                    skipped_count += 1
                    continue
                files.append(logfile)

    return files, skipped_count

def calculate_fields(
    run: MethodRun,
    csv_fields: list,
    process_types: dict,
) -> list:

    start_time = run.start_time
    end_time = run.end_time
    method = run.method or ""

    run_duration = None
    if start_time and end_time:
        run_duration = round((end_time - start_time).total_seconds() / 60, 2)

    run_date = start_time.date().isoformat() if start_time else None

    process_type = None
    method_simplified = None
    for p_type, simplified_methods in process_types.items():
        for simp_name, variants in simplified_methods.items():
            if any(v.casefold() == method.casefold() for v in variants):
                process_type = p_type
                method_simplified = simp_name
                break
        if process_type:
            break

    data = {
        "instrument": run.instrument or "",
        "filename": run.filename or "",
        "start_time": start_time,
        "end_time": end_time,
        "status": run.status,
        "sim_mode": run.sim_mode or "",
        "method": method,
        "run_duration_minutes": run_duration,
        "run_date": run_date,
        "process_type": process_type or "",
        "method_simplified": method_simplified or "",
    }
    return [data.get(key, "") for key, _, _ in csv_fields]

def write_results(
    rows: list,
    output_file: Path,
    fields: list,
) -> None:
    """Write all parsed results to the CSV."""
    with output_file.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # If creating the file, add the headers
        if output_file.stat().st_size == 0:
            writer.writerow([display_name for _, display_name, _ in fields])

        # Add the data
        writer.writerows(rows)

def process_file(logfile: Path) -> List[MethodRun]:
    """Parse one logfile and return the MethodRuns found in it."""
    runs: List[MethodRun] = []
    current_run: Optional[MethodRun] = None
    last_line = None

    with logfile.open("r", encoding="utf-8", errors="ignore") as file:
        for raw_line in file:
            line = raw_line.rstrip("\n")
            last_line = line
            line_lower = line.lower()

            # ---------------------------------------------------------
            # New run detected
            # ---------------------------------------------------------
            if any(pattern in line_lower for pattern in START_PATTERNS.values()):
                # If a previous run never hit an end/abort line, keep it
                # (as Incomplete) before starting the new one.
                if current_run is not None:
                    runs.append(current_run)

                current_run = MethodRun(
                    instrument=logfile.parent.name,
                    filename=logfile.name,
                )
                current_run.start_time = parse_timestamp(line)
                method = parse_method_name(line)
                if method:
                    current_run.method = method
                continue

            # Ignore pre-run information
            if current_run is None:
                continue

            # Method name (fill once)
            if current_run.method is None:
                method = parse_method_name(line)
                if method:
                    current_run.method = method

            # Sim / Live mode (fill once)
            if current_run.sim_mode is None:
                sim_mode = parse_simulation_mode(line)
                if sim_mode:
                    current_run.sim_mode = sim_mode

            # End / abort — this is what actually closes out a run
            if any(pattern in line_lower for pattern in END_PATTERNS.values()):
                current_run.end_time = parse_timestamp(line)
                current_run.status = parse_status(line_lower)
                runs.append(current_run)
                current_run = None

    # ---------------------------------------------------------
    # End of file fallback
    # ---------------------------------------------------------
    if current_run is not None:
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

    processed_folder = log_folder / "Processed"
    files, skipped_count = find_logfiles(log_folder, processed_folder)
    total_files = len(files)

    logger.info(
        f"Found {total_files} files "
        f"({skipped_count} skipped by filename filter)."
    )

    # ---------------------------------------------------------
    # 2. Parse every file
    # ---------------------------------------------------------

    results: List[Tuple[Path, MethodRun]] = []
    for logfile in files:
        try:
            runs = process_file(logfile)
        except OSError as e:
            logger.warning(f"Could not read {logfile.name}: {e}")
            continue

        for run in runs:
            if run.status in STATUSES_TO_DROP:
                continue
            results.append((logfile, run))

    # ---------------------------------------------------------
    # 3. Write all parsed results to CSV
    # ---------------------------------------------------------

    logger.info(f"Writing results to {output_file}")

    tidy_rows = [
        calculate_fields(run, CSV_FIELDS, process_types)
        for _, run in results
    ]
    if tidy_rows:
        write_results(tidy_rows, output_file, CSV_FIELDS)

    # ---------------------------------------------------------
    # 4. Move all parsed files to Processed
    # ---------------------------------------------------------

    if move_files:
        logger.info("Moving parsed files to Processed...")
        moved_already = set()
        for logfile, _ in results:
            if logfile in moved_already:
                continue
            moved_already.add(logfile)

            instrument_folder = logfile.parent.name
            destination_folder = processed_folder / instrument_folder
            destination_folder.mkdir(parents=True, exist_ok=True)
            destination = destination_folder / logfile.name
            try:
                shutil.move(str(logfile), str(destination))
            except OSError as e:
                logger.warning(f"Parsed {logfile.name} but could not move it: {e}")
    else:
        logger.info("Skipping logfile transfer")

    logger.info(f"Finished. {len(tidy_rows)} results saved to {Path(output_file).name}")