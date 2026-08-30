from pathlib import Path
from datetime import datetime
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
import Logfile_Analyser.Generic._GenParseLogs as parse_logs
import csv
import shutil
import re


# =========================================================================
# FUNCTIONS
# =========================================================================

def parse_timestamp(line: str) -> datetime | None:
    timestamp = line.lower()[:19]
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def process_file(logfile: Path, fields: list[tuple[str, str, str]]) -> tuple[Path, list] | None:
    """Parse one logfile and return its path and extracted data."""
    start_time = end_time = method = sim_mode = None
    previous_lines = deque(maxlen=2)
    status = "No Start Found"

    with logfile.open("r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            line_lower = line.lower()

            # Method Name
            if method is None:
                method = parse_method_name(line)

            # Simulation Mode
            if sim_mode is None:
                sim_mode = parse_simulation_mode(line)

            # Start time
            if start_time is None:
                if any(i in line_lower for i in START_PATTERNS.values()):
                    start_time = parse_timestamp(line)
                    status = "Incomplete"
                    if start_time is None:
                        break

            # End / abort
            if start_time is not None:
                if any(i in line_lower for i in END_PATTERNS.values()):
                    end_time = parse_timestamp(previous_lines[-2])
                    status = parse_status(line_lower)
                    break

            # Keep the last two lines for end/abort timestamp lookup
            previous_lines.append(line)

    # Started but no end/abort event found
    if status == "Incomplete":
        end_time = parse_timestamp(previous_lines[-1])

    row_data = {
        "instrument": logfile.parent.name,
        "filename": logfile.name,
        "start_time": start_time,
        "end_time": end_time,
        "status": status,
        "sim_mode": sim_mode,
        "method": method,
    }

    row = [row_data.get(key) for key, _, _ in fields]
    return logfile, row

# =========================================================================
# MAIN PROCESS
# =========================================================================

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

    logger.info(f"Finished parsing {len(results)}/{total_files} files")

