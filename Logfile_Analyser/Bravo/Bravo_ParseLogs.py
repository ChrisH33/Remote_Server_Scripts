from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import Logfile_Analyser.Bravo.Bravo_Config as config
import csv
import shutil
import re

# ============================================================================
# HELPERS
# ============================================================================

def parse_timestamp(value: str):
    for fmt in config.TIMESTAMP_FORMATS:
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

def extract_method(line):
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

@dataclass
class BravoRun:
    instrument: Optional[str] = None
    uniqueID: Optional[str] = None
    status: str = "Incomplete"
    sim_mode: Optional[str] = None
    method: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

# ============================================================================
# PARSER
# ============================================================================

def parse_bravo_file(logfile: Path, logger):
    runs = []
    current_run = None

    try:
        with logfile.open("r", encoding="utf-8", errors="ignore") as file:
            for raw_line in file:
                line = raw_line.rstrip("\n")
                line_lower = line.lower()

                # ---------------------------------------------------------
                # New run detected
                # ---------------------------------------------------------
                if config.PATTERNS["run_start"] in line_lower:
                    if current_run:
                        runs.append(current_run)
                        logger.info("run start appended")

                    current_run = BravoRun()
                    current_run.instrument = logfile.parent.name
                    current_run.start_time = extract_timestamp(line)

                    method = extract_method(line)
                    if method:
                        current_run.method = method

                # Ignore pre-run information
                if current_run is None:
                    continue

                # ---------------------------------------------------------
                # Method extraction
                # ---------------------------------------------------------
                if current_run.method is None:
                    method = extract_method(line)
                    if method:
                        current_run.method = method

                # ---------------------------------------------------------
                # Unique ID
                # ---------------------------------------------------------
                if current_run.method and current_run.start_time:
                    current_run.uniqueID = (
                        f"{current_run.instrument}_"
                        f"{current_run.start_time:%Y%m%d_%H%M%S}_"
                        f"{current_run.method}"
                    )

                # ---------------------------------------------------------
                # Run completion
                # ---------------------------------------------------------
                is_end = any(config.PATTERNS[key] in line_lower for key in config.END_PATTERNS)
                is_abort = any(config.PATTERNS[key] in line_lower for key in config.ABORT_PATTERNS)

                if (is_end or is_abort) and current_run.end_time is None:
                    current_run.end_time = extract_timestamp(line)
                    current_run.status = "Complete" if is_end else "Aborted"

    except OSError:
        return []

    # Save final run
    if current_run:
        runs.append(current_run)

    return runs

# ============================================================================
# CSV OUTPUT
# ============================================================================

def write_results(
    rows: list[list],
    output_file: Path,
    fields: list[tuple[str, str]],
) -> None:
    """Write all parsed results to the CSV."""

    with output_file.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.writer(file)

        if output_file.stat().st_size == 0:
            writer.writerow(
                [display_name for _, display_name in fields]
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
    max_workers,
    logger,
) -> None:
    # ---------------------------------------------------------
    # 1. Find all files
    # ---------------------------------------------------------
    
    logger.info("Looking for files to process...")


    files = []

    ignored = {p.resolve() for p in ignored_folders}
    for entry in log_folder.iterdir():
        if not entry.is_dir() or entry.resolve() in ignored:
            continue
        files.extend(entry.rglob(config.FILE_EXTENSION))
    total_files = len(files)

    logger.info(
        f"Found {total_files} files. "
        f"Processing with {max_workers} workers..."
    )

    # ---------------------------------------------------------
    # 2. Parse every file
    # ---------------------------------------------------------

    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                parse_bravo_file,
                logfile,
                logger,
            ): logfile
            for logfile in files
        }

        for count, future in enumerate(as_completed(futures), start=1):
            logfile = futures[future]

            try:
                result = future.result()
                if result is not None:
                    results.append((logfile, result))
                    if count % 1000 == 0:
                        logger.info(f"Processed {count}/{total_files} files") 
            except Exception:
                logger.exception(f"Error processing {logfile.name}")
    logger.info(f"Parsed {len(results)}/{total_files} files")

    # ---------------------------------------------------------
    # 3. Write all parsed results to CSV
    # ---------------------------------------------------------
    
    runs = [run for _, logfile_runs in results for run in logfile_runs]

    rows = [
        [
            run.instrument,
            run.uniqueID,
            run.start_time,
            run.end_time,
            run.status,
            run.sim_mode,
            run.method,
        ]
        for run in runs
    ]
    existing_ids = set()

    if output_file.exists():
        with output_file.open("r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header
            existing_ids = {row[1] for row in reader if len(row) > 1}
    new_rows = [row for row in rows if row[1] not in existing_ids]
    if new_rows:
        write_results(new_rows, output_file, fields)
        logger.info(f"Saved {len(new_rows)} new results to {output_file}")

    # ---------------------------------------------------------
    # 4. Move all parsed files to Processed
    # ---------------------------------------------------------

    if move_files_after_parse:
        for logfile, _ in results:
            instrument_folder = logfile.parent.name
            destination_folder = (processed_folder / instrument_folder)

            destination_folder.mkdir(parents=True, exist_ok=True)
            destination = (destination_folder / logfile.name)


            try:
                shutil.move(str(logfile), str(destination))
            except OSError as e:
                logger.warning(
                    f"Parsed {logfile.name}, "
                    f"but could not move it: {e}"
                )
    else:
        logger.info("Skipping logfile transfer")

    logger.info(
        f"Finished. {len(rows)} results saved to {Path(output_file).name}"
    )