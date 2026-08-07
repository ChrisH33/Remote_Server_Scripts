from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import os
import re


# ============================================================================
# CONFIG
# ============================================================================

MAX_WORKERS = min(4, os.cpu_count() or 4)
FILE_EXTENSION = "*.log"
TIMESTAMP_FORMATS = (
    "%m/%d/%Y %I:%M:%S %p",
    "%d/%m/%Y %H:%M:%S",
)
PATTERNS = {
    "run_start": "startup protocol starting",
    "runset": "starting runset :",
    "protocol_added": "runset manager: added the run",
    "protocol_file": ".pro",
    "error": "error",
    "warning": "warning",
    "complete": "scheduler stopped",
    "logout": "logged out",
}

# ============================================================================
# FUNCTIONS
# ============================================================================

def parse_timestamp(value: str):
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            pass

    return None

def extract_timestamp(line):
    """
    First tab-separated field is the timestamp.
    """

    parts = line.split("\t")

    if not parts:
        return None

    return parse_timestamp(parts[0])

def extract_protocol(line):
    """
    Extract .pro filename from a Bravo line.
    """

    match = re.search(
        r"([^\\]+\.pro)",
        line,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None

def extract_runset(line):

    match = re.search(
        r"starting runset\s*:\s*(.+)",
        line,
        re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return None

# ============================================================================
# RUN OBJECT
# ============================================================================

class BravoRun:

    def __init__(self, logfile):

        self.logfile = logfile

        self.instrument = None
        self.runset = None
        self.protocol = None

        self.start_time = None
        self.end_time = None

        self.status = "Incomplete"

        self.errors = 0
        self.warnings = 0


    def to_row(self):

        return [
            self.logfile.name,
            self.instrument,
            self.runset,
            self.protocol,
            self.start_time,
            self.end_time,
            self.status,
            self.errors,
            self.warnings,
        ]

# ============================================================================
# PARSER
# ============================================================================

def parse_bravo_file(logfile: Path):
    runs = []
    current_run = None

    try:
        with logfile.open(
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as file:
            for raw_line in file:
                line = raw_line.rstrip("\n")
                lower = line.lower()
                timestamp = extract_timestamp(line)

                # ---------------------------------------------------------
                # New run detected
                # ---------------------------------------------------------
                if PATTERNS["run_start"] in lower:
                    if current_run:
                        runs.append(current_run)
                    current_run = BravoRun(logfile)
                    current_run.start_time = timestamp
                    protocol = extract_protocol(line)

                    if protocol:
                        current_run.protocol = protocol

                # Ignore pre-run information
                if current_run is None:
                    continue

                # ---------------------------------------------------------
                # Runset
                # ---------------------------------------------------------

                if PATTERNS["runset"] in lower:
                    current_run.runset = extract_runset(line)

                # ---------------------------------------------------------
                # Protocol extraction
                # ---------------------------------------------------------
                if current_run.protocol is None:
                    protocol = extract_protocol(line)
                    if protocol:
                        current_run.protocol = protocol

                # ---------------------------------------------------------
                # Instrument
                # ---------------------------------------------------------
                if current_run.instrument is None:
                    match = re.search(
                        r"(Bravo\s*-\s*\d+)",
                        line,
                        re.IGNORECASE,
                    )

                    if match:
                        current_run.instrument = match.group(1)

                # ---------------------------------------------------------
                # Errors / warnings
                # ---------------------------------------------------------
                if "\terror\t" in lower:
                    current_run.errors += 1

                elif "\twarning\t" in lower:
                    current_run.warnings += 1

                # ---------------------------------------------------------
                # Run completion
                # ---------------------------------------------------------

                if (
                    PATTERNS["logout"] in lower
                    or PATTERNS["complete"] in lower
                ):

                    current_run.end_time = timestamp
                    current_run.status = "Complete"



    except OSError:

        return []



    # Save final run

    if current_run:

        runs.append(current_run)



    return runs



# ============================================================================
# CSV OUTPUT
# ============================================================================


FIELDS = [
    ("filename", "Filename"),
    ("instrument", "Instrument"),
    ("runset", "Runset"),
    ("protocol", "Protocol"),
    ("start_time", "Start Time"),
    ("end_time", "End Time"),
    ("status", "Status"),
    ("errors", "Errors"),
    ("warnings", "Warnings"),
]


def write_results(
    rows,
    output_file: Path,
):

    exists = output_file.exists()

    with output_file.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        if not exists:

            writer.writerow(
                [
                    name
                    for _, name in FIELDS
                ]
            )

        writer.writerows(rows)



# ============================================================================
# MAIN PARSER
# ============================================================================


def run_parser(
    log_folder: Path,
    processed_folder: Path,
    ignored_folders: set[Path],
    output_file: Path,
    fields: list[tuple[str, str]],
    move_files_after_parse: bool,
    logger,
) -> None:

    logger.info("=== Log parser starting ===")

    # ---------------------------------------------------------
    # 1. Find all files
    # ---------------------------------------------------------
    
    logger.info("Looking for files to process...")


    files = []

    ignored = {p.resolve() for p in ignored_folders}
    for entry in log_folder.iterdir():
        if not entry.is_dir() or entry.resolve() in ignored:
            continue
        files.extend(entry.rglob(FILE_EXTENSION))
    total_files = len(files)

    logger.info(
        f"Found {total_files} files. "
        f"Processing with {MAX_WORKERS} workers..."
    )
    
    # ---------------------------------------------------------
    # 2. Parse every file
    # ---------------------------------------------------------


    with ProcessPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:


        futures = {
            executor.submit(
                parse_bravo_file,
                file,
            ): file
            for file in files
        }


        for future in as_completed(futures):

            logfile = futures[future]

            try:

                runs = future.result()

                for run in runs:

                    results.append(
                        run.to_row()
                    )


            except Exception as e:

                print(
                    f"Failed {logfile}: {e}"
                )



    if results:

        write_results(
            results,
            output_file,
        )



    print(
        f"Processed {len(files)} Bravo logs"
    )

    print(
        f"Extracted {len(results)} runs"
    )