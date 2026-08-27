import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

# =========================================================================
# CONFIG OBJECT
# Bundles the "which files / folders / thresholds" concerns into a single
# value so callers pass one thing instead of five positional args, and so
# tests can build a StaleCheckConfig pointed at tmp_path without touching
# Main_Config at all.
# =========================================================================

@dataclass(frozen=True)
class StaleCheckConfig:
    tidy_csv: Path          # Tidy log CSV to read "last seen" times from
    log_folder: Path        # Folder containing one subfolder per instrument
    processed_folder: Path  # Subfolder of log_folder to ignore
    warning_file: Path      # Where to write/clear the stale-instrument warning
    stale_days: int         # How many days of silence counts as "stale"

# =========================================================================
# READING "LAST SEEN" TIMES
# =========================================================================

def _parse_start_time(value: str | None) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def _last_seen_by_instrument(tidy_csv: Path) -> dict[str, datetime]:
    """Return the most recent recorded start time for each instrument."""
    last_seen: dict[str, datetime] = {}
    with tidy_csv.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            instrument = (row.get("Instrument") or "").strip()
            start_time = _parse_start_time(row.get("Start Time"))
            if not instrument or start_time is None:
                continue
            if instrument not in last_seen or start_time > last_seen[instrument]:
                last_seen[instrument] = start_time
    return last_seen

# =========================================================================
# FINDING STALE INSTRUMENTS
# =========================================================================

def _instrument_dirs(log_folder: Path, processed_folder: Path) -> list[Path]:
    """Return instrument subfolders of log_folder, excluding processed_folder."""
    ignored = processed_folder.resolve()
    return [p for p in log_folder.iterdir() if p.is_dir() and p.resolve() != ignored]

def _find_stale(
    instrument_dirs: list[Path],
    last_seen: dict[str, datetime],
    cutoff: datetime,
) -> list[tuple[str, datetime | None]]:
    """Return (instrument, last_seen) for every instrument with no recent activity."""
    stale = []
    for instrument_dir in instrument_dirs:
        instrument = instrument_dir.name
        seen = last_seen.get(instrument)
        if seen is None or seen < cutoff:
            stale.append((instrument, seen))
    return stale

# =========================================================================
# LOGGING + WARNING FILE
# =========================================================================

def _log_stale(stale: list[tuple[str, datetime | None]], logger, now: datetime) -> None:
    for instrument, seen in stale:
        if seen is None:
            logger.warning(f"No recorded activity at all for instrument: {instrument}")
        else:
            logger.warning(f"{instrument} last active {(now - seen).days} days ago ({seen})")

def _format_warning_line(instrument: str, last_seen: datetime | None) -> str:
    if last_seen:
        return f"Serial: {instrument} - last seen {last_seen.date().isoformat()}"
    return f"Serial: {instrument} - no activity on record"

def _write_warning_file(
    warning_file: Path,
    stale: list[tuple[str, datetime | None]],
    stale_days: int,
    logger,
) -> None:
    lines = [
        f"The following instrument(s) have not reported activity in over {stale_days} days:",
        "",
    ]
    lines += [_format_warning_line(instrument, seen) for instrument, seen in stale]
    try:
        warning_file.write_text("\n".join(lines), encoding="utf-8")
    except OSError as e:
        logger.error(f"Could not write {warning_file}: {e}")

def _clear_warning_file(warning_file: Path, logger) -> None:
    if not warning_file.exists():
        return
    try:
        warning_file.unlink()
        logger.info(f"Removed stale {warning_file} from a previous run.")
    except OSError as e:
        logger.warning(f"Could not remove old {warning_file}: {e}")

# =========================================================================
# ENTRY POINT
# =========================================================================

def check_stale_instruments(cfg: StaleCheckConfig, logger) -> None:
    logger.info("Checking instrument activity")
    now = datetime.now()
    cutoff = now - timedelta(days=cfg.stale_days)

    last_seen = _last_seen_by_instrument(cfg.tidy_csv)
    instrument_dirs = _instrument_dirs(cfg.log_folder, cfg.processed_folder)
    stale = _find_stale(instrument_dirs, last_seen, cutoff)

    if not stale:
        logger.info(f"All instruments have reported activity within the last {cfg.stale_days} days.")
        _clear_warning_file(cfg.warning_file, logger)
        return

    _log_stale(stale, logger, now)
    _write_warning_file(cfg.warning_file, stale, cfg.stale_days, logger)