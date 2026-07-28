import csv
from pathlib import Path
from datetime import datetime, timedelta

def check_stale_instruments(
    file: Path,
    stale_days: int,
    log_folder: Path,
    processed_folder: Path,
    warning_file: Path,
    logger
) -> None:
    logger.info(">> Checking instrument activity")

    # === Declare Variables ===
    now = datetime.now()
    cutoff = now - timedelta(days=stale_days)
    stale_instruments = []

    # === Find the last time each instrument was seen ===
    last_seen: dict[str, datetime] = {}
    with open(file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            instrument = (row.get("Instrument") or "").strip()
            start_str = (row.get("Start Time") or "").strip()
            if not instrument or not start_str:
                continue
            try:
                start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if instrument not in last_seen or start_time > last_seen[instrument]:
                last_seen[instrument] = start_time

    # === Find all of the instrument folders ===
    processed_resolved = processed_folder.resolve()
    instrument_folders = [
        d for d in log_folder.iterdir()
        if d.is_dir() and d.resolve() != processed_resolved
    ]

    # === Compare the last time an instrument was seen w/ the cuttoff ===
    stale_instruments = []
    for instrument_dir in instrument_folders:
        instrument = instrument_dir.name
        last_seen_date = last_seen.get(instrument)

        if last_seen_date is None:
            logger.warning(f"No recorded activity at all for instrument: {instrument}")
            stale_instruments.append((instrument, None))
        elif last_seen_date < cutoff:
            days_ago = (now - last_seen_date).days
            logger.warning(f"{instrument} last active {days_ago} day(s) ago ({last_seen_date})")
            stale_instruments.append((instrument, last_seen_date))

    if not stale_instruments:
        logger.info(f"All instruments have reported activity within the last {stale_days} days.")
        if warning_file.exists():
            try:
                warning_file.unlink()
                logger.info(f"Removed stale {warning_file} from a previous run.")
            except OSError as e:
                logger.warning(f"Could not remove old {warning_file}: {e}")
        return

    lines = [
        f"The following instrument(s) have not reported activity in over {stale_days} days:",
        "",
    ]
    for instrument, last_seen_date in stale_instruments:


        if last_seen_date:
            lines.append(
                f"Serial: {instrument} - last seen {last_seen_date.date().isoformat()}"
            )
        else:
            lines.append(f"Serial: {instrument} - no activity on record")

    try:
        warning_file.write_text("\n".join(lines), encoding="utf-8")
        logger.warning(f"Wrote {warning_file} listing {len(stale_instruments)} stale instrument(s).")
    except OSError as e:
        logger.error(f"Could not write {warning_file}: {e}")