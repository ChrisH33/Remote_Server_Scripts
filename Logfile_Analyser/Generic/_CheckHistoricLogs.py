import csv
from pathlib import Path
from datetime import datetime, timedelta


def _last_seen_by_instrument(file: Path) -> dict[str, datetime]:
    last_seen: dict[str, datetime] = {}
    with open(file, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
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
    return last_seen


def _find_stale(log_folder: Path, processed_folder: Path, last_seen: dict, cutoff: datetime, now: datetime, logger):
    ignored = {processed_folder.resolve()}
    stale = []
    for instrument_dir in log_folder.iterdir():
        if not instrument_dir.is_dir() or instrument_dir.resolve() in ignored:
            continue
        instrument = instrument_dir.name
        last_seen_date = last_seen.get(instrument)
        if last_seen_date is None:
            logger.warning(f"No recorded activity at all for instrument: {instrument}")
            stale.append((instrument, None))
        elif last_seen_date < cutoff:
            logger.warning(f"{instrument} last active {(now - last_seen_date).days} day(s) ago ({last_seen_date})")
            stale.append((instrument, last_seen_date))
    return stale


def _write_warning_file(warning_file: Path, stale: list, stale_days: int, logger) -> None:
    lines = [f"The following instrument(s) have not reported activity in over {stale_days} days:", ""]
    lines += [
        f"Serial: {inst} - {'last seen ' + seen.date().isoformat() if seen else 'no activity on record'}"
        for inst, seen in stale
    ]
    try:
        warning_file.write_text("\n".join(lines), encoding="utf-8")
    except OSError as e:
        logger.error(f"Could not write {warning_file}: {e}")


def _clear_warning_file(warning_file: Path, logger) -> None:
    if warning_file.exists():
        try:
            warning_file.unlink()
            logger.info(f"Removed stale {warning_file} from a previous run.")
        except OSError as e:
            logger.warning(f"Could not remove old {warning_file}: {e}")


def check_stale_instruments(
    file: Path,
    stale_days: int,
    log_folder: Path,
    processed_folder: Path,
    warning_file: Path,
    logger
) -> None:
    logger.info("Checking instrument activity")
    now = datetime.now()
    cutoff = now - timedelta(days=stale_days)

    last_seen = _last_seen_by_instrument(file)
    stale = _find_stale(log_folder, processed_folder, last_seen, cutoff, now, logger)

    if not stale:
        logger.info(f"All instruments have reported activity within the last {stale_days} days.")
        _clear_warning_file(warning_file, logger)
        return

    _write_warning_file(warning_file, stale, stale_days, logger)