from pathlib import Path
from datetime import datetime
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
import Logfile_Analyser.Hamilton.Ham_Config as config
import Logfile_Analyser.Main_Config as general_config
import csv
import shutil

files_to_drop = general_config.FILENAME_PREFIXES_TO_DROP
move_files = general_config.MOVE_FILES_AFTER_PARSE
csv_fields = general_config.CSV_FIELDS
max_workers = general_config.MAX_WORKERS
skip_lines = general_config.SKIP_LINES



# =========================================================================
# BASE FUNCTIONS
# =========================================================================

def parse_timestamp(line: str) -> datetime | None:
    timestamp = line.lower()[:19]
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def parse_method_name(line: str):
    match = config.METHOD_RE.search(line)
    if match:
        return match.group(1)
    return None

def parse_status(line: str):
    for key, pattern in config.END_PATTERNS.items():
        if pattern in line:
            if key.startswith("abort"):
                return "Aborted"
            return "Complete"
    return None

def parse_simulation_mode(line: str):
    match = config.SERIAL_RE.search(line)
    if match:
        serial = match.group(1).strip()
        return "Sim" if serial == "0000" else "Live"
    return None

# =========================================================================
# COMPLEX FUNCTIONS
# =========================================================================

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
            if start_time is None and any(i in line_lower for i in config.START_PATTERNS.values()):
                start_time = parse_timestamp(line)
                if start_time is None:
                    break

            # End / abort
            if start_time is not None:
                if not any(i in line_lower for i in skip_lines):
                    if end_time is None and any(i in line_lower for i in config.END_PATTERNS.values()):
                        end_time = parse_timestamp(previous_lines[-2])
                        status = parse_status(line_lower)
                        break

            # Keep the last two lines for end/abort timestamp lookup
            previous_lines.append(line)

    # Started but no end/abort event found
    if start_time is not None:
        status = "Incomplete"
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

def write_results(rows: list[list], output_file: Path, fields: list[tuple[str, str, str]]) -> None:
    """Write all parsed results to the CSV."""
    with output_file.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # If creating the file, add the headers
        if output_file.stat().st_size == 0:
            writer.writerow([display_name for _, display_name, _ in fields])

        # Add the data
        writer.writerows(rows)

# =========================================================================
# MAIN PROCESS
# =========================================================================

def run_parser(log_folder: Path, processed_folder: Path, output_file: Path, logger) -> None:

    logger.info("=== Log parser starting ===")

    # ---------------------------------------------------------
    # 1. Find all files
    # ---------------------------------------------------------

    logger.info("Looking for files to process...")

    files = []
    skipped_count = 0

    ignored = {p.resolve() for p in {processed_folder}}
    lowered_prefixes = tuple(prefix.lower() for prefix in files_to_drop)

    for entry in log_folder.iterdir():
        if not entry.is_dir() or entry.resolve() in ignored:
            continue

        for logfile in entry.rglob(config.FILE_EXTENSION):
            if logfile.name.lower().startswith(lowered_prefixes):
                skipped_count += 1
                continue

            files.append(logfile)

    total_files = len(files)

    logger.info(
        f"Found {total_files} files "
        f"({skipped_count} skipped by filename filter). "
        f"Processing with {max_workers} workers..."
    )

    # ---------------------------------------------------------
    # 2. Parse every file
    # ---------------------------------------------------------

    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_file, logfile, fields=csv_fields): logfile
            for logfile in files
        }

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

    # ---------------------------------------------------------
    # 3. Write all parsed results to CSV
    # ---------------------------------------------------------

    logger.info(f"Writing results to {output_file}")

    rows = [row for _, row in results]
    existing_ids = set()

    if output_file.exists():
        with output_file.open("r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header
            existing_ids = {row[1] for row in reader if len(row) > 1}
    new_rows = [row for row in rows if row[1] not in existing_ids]
    if new_rows:
        write_results(new_rows, output_file, csv_fields)
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