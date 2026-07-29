from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import re
import shutil

def parse_timestamp(
    line: str,
    filename: str,
    logger
) -> datetime | None:
    timestamp = line[:19]
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        logger.warning(f"{filename}: Invalid timestamp {timestamp!r}")
        return None

def process_file(
    logfile: Path,
    logger,
    *,
    patterns: dict[str, str],
    end_patterns: tuple[str, ...],
    abort_patterns: tuple[str, ...],
    method_re: re.Pattern,
    serial_re: re.Pattern,
    fields: list[tuple[str, str]],
) -> tuple[Path, list] | None:
    """Parse one logfile and return its path and extracted data."""

    start_time = None
    end_time = None
    status = None
    method = None

    tips_96MPH = 0
    tips_384MPH = 0
    sim_mode = "Sim"

    # The timestamp for an end/abort event is two lines before
    # the event line.
    previous_lines = []

    try:
        with logfile.open("r", encoding="utf-8", errors="ignore") as file:
            for line_number, line in enumerate(file, start=1):
                line_lower = line.lower()

                # Method name
                if method is None and patterns["Method Name"] in line_lower:
                    match = method_re.search(line)
                    if match:
                        method = match.group(1)

                # Serial number / simulation mode
                if sim_mode == "Sim" and patterns["serial"] in line_lower:
                    match = serial_re.search(line)

                    if match:
                        serial = match.group(1).strip()
                        sim_mode = "Sim" if serial == "0000" else "Live"
                    else:
                        sim_mode = "undefined"

                # Tip pickup counts
                if patterns["96 MPH Pickup"] in line_lower:
                    tips_96MPH += 1
                elif patterns["384 MPH Pickup"] in line_lower:
                    tips_384MPH += 1

                # Start time
                if start_time is None:
                    if patterns["start"] in line_lower:
                        start_time = parse_timestamp(line, logfile.name, logger)
                        if start_time is None:
                            break

                # End / abort
                elif (
                    any(patterns[key] in line_lower for key in end_patterns)
                    or any(patterns[key] in line_lower for key in abort_patterns)
                ):
                    if len(previous_lines) >= 2:
                        end_time = parse_timestamp(previous_lines[-2], logfile.name, logger)
                    if any(patterns[key] in line_lower for key in end_patterns):
                        status = "Complete"
                    else:
                        status = "Aborted"
                    break

                # Keep the last two lines for end/abort timestamp lookup
                previous_lines.append(line)

                if len(previous_lines) > 2:
                    previous_lines.pop(0)

    except OSError as e:
        logger.error(f"Failed to read {logfile}: {e}")
        status = "Read Error"

    # Started but no end/abort event found
    if start_time is not None and status is None:
        status = "Incomplete"

        if previous_lines:
            end_time = parse_timestamp(
                previous_lines[-1],
                logfile.name,
                logger,
            )

    # No start event found
    elif start_time is None and status is None:
        status = "No Start Found"

    info = {
        "start_time": start_time,
        "end_time": end_time,
        "status": status,
        "sim_mode": sim_mode,
        "method": method,
        "tips_96MPH": tips_96MPH,
        "tips_384MPH": tips_384MPH,
    }

    instrument = logfile.parent.name

    row_data = {
        "instrument": instrument,
        "filename": logfile.name,
        **info,
    }

    row = [row_data.get(key) for key, _ in fields]

    return logfile, row

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

def run_parser(
    *,
    log_folder: Path,
    processed_folder: Path,
    output_file: Path,
    patterns: dict[str, str],
    end_patterns: tuple[str, ...],
    abort_patterns: tuple[str, ...],
    method_re: re.Pattern,
    serial_re: re.Pattern,
    fields: list[tuple[str, str]],
    file_ext: str,
    max_workers: int,
    move_files_after_parse: bool,
    logger,
) -> None:

    logger.info("=== Log parser starting ===")

    # ---------------------------------------------------------
    # 1. Find all files
    # ---------------------------------------------------------

    logger.info("Looking for files to process...")

    files = list(log_folder.rglob(file_ext))
    if not files:
        logger.info("Nothing to do - exiting.")
        return
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
                process_file,
                logfile,
                logger,
                patterns=patterns,
                end_patterns=end_patterns,
                abort_patterns=abort_patterns,
                method_re=method_re,
                serial_re=serial_re,
                fields=fields,
            ): logfile
            for logfile in files
        }

        for count, future in enumerate(
            as_completed(futures),
            start=1,
        ):
            logfile = futures[future]

            try:
                result = future.result()

                if result is not None:
                    results.append(result)

            except Exception:
                logger.exception(
                    f"Error processing {logfile.name}"
                )

    logger.info(
        f"Finished parsing {len(results)}/{total_files} files"
    )

    # ---------------------------------------------------------
    # 3. Write all parsed results to CSV
    # ---------------------------------------------------------

    rows = [row for _, row in results]
    existing_ids = set()

    if output_file.exists():
        with output_file.open("r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header

            existing_ids = {
                row[1]
                for row in reader
                if len(row) > 1
            }

    new_rows = [
        row
        for row in rows
        if row[1] not in existing_ids
    ]

    if new_rows:
        write_results(
            new_rows,
            output_file,
            fields,
        )

        logger.info(
            f"Saved {len(new_rows)} new results to {output_file}"
        )
    else:
        logger.info("No new results to save")

    # ---------------------------------------------------------
    # 4. Move all parsed files to Processed
    # ---------------------------------------------------------

    logger.info("Moving parsed files to Processed...")
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