from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import Logfile_Analyser.Main_Config as config
import Logfile_Analyser.Generic._GenParseLogs as parse_logs
import csv
import shutil
import re


# =========================================================================
# FUNCTIONS
# =========================================================================

def parse_timestamp(line: str) -> datetime | None:
    value = line.split("\t", 1)[0].strip()
    if not value:
        return None

    for fmt in config.TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


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

# ============================================================================
# MAIN PARSER
# ============================================================================

def run_parser(log_folder: Path, output_file: Path, logger) -> None:

    logger.info("=== Log parser starting ===")


    # ---------------------------------------------------------
    # 2. Parse every file
    # ---------------------------------------------------------

    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, logfile,): logfile for logfile in files}

        for count, future in enumerate(as_completed(futures), start=1):
            logfile = futures[future]
            try:
                result = future.result()
                results.append(result) if result is not None else None

                # Occasional update log
                if count % 1000 == 0:
                    logger.info(f"Processed {count}/{total_files} files")
                    
            except Exception:
                logger.exception(f"Error processing {logfile.name}")

    logger.info(f"Parsed {len(results)}/{total_files} files")

    # ---------------------------------------------------------
    # 3. Write all parsed results to CSV
    # ---------------------------------------------------------

    logger.info(f"Writing results to {output_file}")

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
        parse_logs.write_results(new_rows, output_file, csv_fields)
        logger.info(f"Saved {len(new_rows)} new results to {output_file}")
    else:
        logger.info("No new results to save")

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