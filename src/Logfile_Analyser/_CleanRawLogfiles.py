import csv
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd


def get_unique_ids(df: pd.DataFrame) -> set:
    """Return unique IDs from column 2 of a DataFrame."""
    return set(df.iloc[:, 1].dropna())

def extract_process_type(
    method: str,
    process_types: dict[str, list[str]],
    logger: logging.Logger,
) -> str:
    try:
        text = method.upper()
    except AttributeError:
        logger.warning(f"Invalid method: {method!r}")
        return "Unknown"

    for process_type, substrings in process_types.items():
        if any(s.upper() in text for s in substrings):
            return process_type

    return "Unknown"

def parse_base_method(
    method: str,
    method_simplified: dict[str, list[str]],
    logger: logging.Logger,
) -> str:
    try:
        text = method.upper().strip()
    except AttributeError:
        logger.warning(f"Invalid method: {method!r}")
        return "Unknown"

    for method_base, methods in method_simplified.items():
        if any(m.upper().strip() == text for m in methods):
            return method_base

    return method

def extract_pipeline(
    method: str,
    pipeline_codes: set[str],
    logger: logging.Logger,
) -> str:
    try:
        tokens = method.upper().split("_")
    except AttributeError:
        logger.warning(f"Invalid method: {method!r}")
        return "Unknown"

    for token in tokens:
        if token in pipeline_codes:
            return token

    return "Unknown"

def extract_run_date(
    timestamp: datetime | None,
) -> str:
    if timestamp:
        return timestamp.date().isoformat()

    return ""

def calculate_run_duration(
    start_time: datetime | None,
    end_time: datetime | None,
) -> float | str:
    if start_time and end_time:
        return round(
            (end_time - start_time).total_seconds() / 60,
            2,
        )

    return ""

def parse_datetime(
    value: str,
    logger: logging.Logger,
) -> datetime | None:

    if value is None:
        logger.warning("Missing datetime value")
        return None

    value = str(value).strip()

    if not value:
        logger.warning("Missing datetime value")
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d %H:%M:%S",
        )

    except ValueError:
        logger.warning(
            f"Could not parse datetime value: {value!r}"
        )
        return None

def add_calculated_fields(
    method: str,
    start_time: datetime | None,
    end_time: datetime | None,
    *,
    process_types: dict[str, list[str]],
    method_simplified: dict[str, list[str]],
    pipeline_codes: set[str],
    logger: logging.Logger,
) -> dict:

    return {
        "run_duration_minutes": calculate_run_duration(
            start_time,
            end_time,
        ),
        "run_date": extract_run_date(start_time),
        "pipeline": extract_pipeline(
            method,
            pipeline_codes,
            logger,
        ),
        "process_type": extract_process_type(
            method,
            process_types,
            logger,
        ),
        "method_simplified": parse_base_method(
            method,
            method_simplified,
            logger,
        ),
    }

def clean_row(
    raw_row: dict,
    *,
    statuses_to_drop: set[str],
    filename_prefixes_to_drop: tuple[str, ...],
    process_types: dict[str, list[str]],
    method_simplified: dict[str, list[str]],
    pipeline_codes: set[str],
    tidy_fields: list[tuple[str, str, str]],
    logger: logging.Logger,
) -> list | None:

    status = (raw_row.get("Status") or "").strip()
    filename = (raw_row.get("Filename") or "").strip()

    # Drop unwanted statuses
    if status in statuses_to_drop:
        return None

    # Drop unwanted filenames
    if filename.startswith(filename_prefixes_to_drop):
        return None

    method = raw_row.get("Method", "")

    start_time = parse_datetime(
        raw_row.get("Start Time", ""),
        logger,
    )

    end_time = parse_datetime(
        raw_row.get("End Time", ""),
        logger,
    )

    tidy_data = {
        # IMPORTANT:
        # Keep the unique ID in the tidy CSV.
        # Adjust "Unique ID" to match your actual raw CSV column name.
        "unique_id": raw_row.get("Unique ID", ""),

        "instrument": raw_row.get("Instrument", ""),
        "filename": raw_row.get("Filename", ""),
        "start_time": start_time,
        "end_time": end_time,
        "status": status,
        "sim_mode": raw_row.get("Sim Mode", ""),
        "method": method,
        "tips_96MPH": raw_row.get("tips 96MPH", ""),
        "tips_384MPH": raw_row.get("tips 384MPH", ""),

        **add_calculated_fields(
            method,
            start_time,
            end_time,
            process_types=process_types,
            method_simplified=method_simplified,
            pipeline_codes=pipeline_codes,
            logger=logger,
        ),
    }

    return [
        tidy_data.get(key, "")
        for key, _, _ in tidy_fields
    ]

def run_cleaner(
    *,
    raw_input_file: Path,
    tidy_output_file: Path,
    tidy_fields: list[tuple[str, str, str]],
    statuses_to_drop: set[str],
    filename_prefixes_to_drop: tuple[str, ...],
    process_types: dict[str, list[str]],
    method_simplified: dict[str, list[str]],
    pipeline_codes: set[str],
    logger: logging.Logger,
) -> None:

    logger.info("=== Tidy-up script starting ===")


    # Check raw input exists
    if not raw_input_file.exists():
        logger.error(f"Raw input file not found: {raw_input_file}")
        return

    # Read existing tidy data
    try:
        tidy_df = pd.read_csv(tidy_output_file)
        existing_ids = get_unique_ids(tidy_df)
        logger.info(f"Found {len(existing_ids)} existing IDs in tidy CSV")
    except FileNotFoundError:
        existing_ids = set()
        logger.info("Tidy CSV not found. Starting with no existing IDs.")

    # Read raw data
    raw_df = pd.read_csv(raw_input_file)
    potential_ids = get_unique_ids(raw_df)
    logger.info(f"Found {len(potential_ids)} unique IDs in raw CSV")

    # Find new IDs
    new_ids = potential_ids - existing_ids
    if not new_ids:
        logger.info("No new rows to process.")
        return
    logger.info(f"Found {len(new_ids)} new IDs")

    # Get rows belonging to new IDs
    new_rows = raw_df[raw_df.iloc[:, 1].isin(new_ids)].copy()
    logger.info(f"Found {len(new_rows)} new rows to process")

    # ---------------------------------------------------------
    # Clean new rows
    # ---------------------------------------------------------

    tidy_rows = []
    dropped_count = 0
    error_count = 0

    for _, raw_row in new_rows.iterrows():
        try:
            tidy_row = clean_row(
                raw_row.to_dict(),
                statuses_to_drop=statuses_to_drop,
                filename_prefixes_to_drop=filename_prefixes_to_drop,
                process_types=process_types,
                method_simplified=method_simplified,
                pipeline_codes=pipeline_codes,
                tidy_fields=tidy_fields,
                logger=logger,
            )
        except Exception:
            logger.exception(f"Error cleaning row: {raw_row.to_dict()}")
            error_count += 1
            continue
        if tidy_row is None:
            dropped_count += 1
        else:
            tidy_rows.append(tidy_row)

    # ---------------------------------------------------------
    # Append cleaned rows to tidy CSV
    # ---------------------------------------------------------

    if tidy_rows:
        header_needed = not tidy_output_file.exists()
        with open(tidy_output_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if header_needed:
                writer.writerow([display_name for _, display_name, _ in tidy_fields])
            writer.writerows(tidy_rows)
        logger.info(f"Wrote {len(tidy_rows)} new rows to {tidy_output_file}")
    else:
        logger.info("No rows passed the cleaning rules. Nothing written to tidy CSV.")

    logger.info(
        f"Finished. "
        f"{len(tidy_rows)} written, "
        f"{dropped_count} dropped, "
        f"{error_count} errors."
    )