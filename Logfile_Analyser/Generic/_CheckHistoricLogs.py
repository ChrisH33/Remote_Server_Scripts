import csv
from datetime import datetime, timedelta
from pathlib import Path

# =========================================================================
# READING "LAST SEEN" TIMES
# =========================================================================

def delete_file(warning_file):
    try:
        warning_file.unlink(missing_ok=True)
    except OSError as e:
        raise RuntimeError(f"Could not clear warning file {warning_file}") from e

def get_last_seen_per_instrument(tidy_csv):
    """Return the most recent recorded start time for each instrument."""
    last_seen: dict[str, datetime] = {}
    with tidy_csv.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            instrument = (row.get("Instrument") or "").strip()
            start_time = datetime.strptime(row["Start Time"].strip(),"%Y-%m-%d %H:%M:%S")
            if not instrument:
                continue
            if (instrument not in last_seen or start_time > last_seen[instrument]):
                last_seen[instrument] = start_time
    return last_seen

# =========================================================================
# LOGGING + WARNING FILE
# =========================================================================

def write_stale_warning(warning_file, stale, stale_days):
    lines = [
        f"The following instrument(s) have not reported activity "
        f"in over {stale_days} days:",
        "",
        *(
            f"Serial: {instrument} - last seen {last_seen.date().isoformat()}"
            for instrument, last_seen in stale
        ),
    ]

    try:
        warning_file.write_text("\n".join(lines), encoding="utf-8")
    except OSError as e:
        raise RuntimeError(f"Could not write warning file {warning_file}") from e
    
# =========================================================================
# ENTRY POINT
# =========================================================================

def check_stale_instruments(log_csv: Path, output_txt: Path, logger, *, stale_days: int = 45) -> None:
    now = datetime.now()
    cutoff = now - timedelta(days=stale_days)

    try:
        delete_file(output_txt)
    except RuntimeError as e: 
        logger.error(e)

    # ---------------------------------------------------------
    # 1. Find Instruments to Check
    # ---------------------------------------------------------

    logger.info("Checking instrument activity")

    last_seen = get_last_seen_per_instrument(log_csv)
    if not last_seen:
        logger.info(f"No instrument activity found in {log_csv}")
        return

    # ---------------------------------------------------------
    # 2. Find Stale Instruments
    # ---------------------------------------------------------

    stale: list[tuple[str, datetime]] = []
    for instrument, date in last_seen.items():
        if date < cutoff:
            stale.append((instrument, date))

    # ---------------------------------------------------------
    # 3. Write Warning File
    # ---------------------------------------------------------

    if stale:
        write_stale_warning(output_txt, stale, stale_days,)
        logger.warning(f"Found {len(stale)} stale instrument(s)")
    else:
        logger.info(
            f"All instruments have reported activity "
            f"within the last {stale_days} days."
        )