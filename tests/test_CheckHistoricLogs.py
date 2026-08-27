from datetime import datetime, timedelta

from Logfile_Analyser.Generic._CheckHistoricLogs import (
    StaleCheckConfig,
    _parse_start_time,
    _last_seen_by_instrument,
    _instrument_dirs,
    _find_stale,
    _format_warning_line,
    _write_warning_file,
    _clear_warning_file,
    check_stale_instruments,
)


# =========================================================================
# _parse_start_time
# =========================================================================

def test_ParseStartTime_Valid():
    assert _parse_start_time("2024-01-15 09:30:00") == datetime(2024, 1, 15, 9, 30, 0)

def test_ParseStartTime_EmptyString():
    assert _parse_start_time("") is None

def test_ParseStartTime_None():
    assert _parse_start_time(None) is None

def test_ParseStartTime_Malformed():
    assert _parse_start_time("15/01/2024 09:30") is None

# =========================================================================
# _last_seen_by_instrument
# =========================================================================

def test_LastSeenBy_PickRecentRow(tmp_path):
    csv_file = tmp_path / "tidy.csv"
    csv_file.write_text(
        "Instrument,Start Time\n"
        "STAR1,2024-01-01 08:00:00\n"
        "STAR1,2024-01-10 08:00:00\n"
        "STAR1,2024-01-05 08:00:00\n",
        encoding="utf-8",
    )
    result = _last_seen_by_instrument(csv_file)
    assert result == {"STAR1": datetime(2024, 1, 10, 8, 0, 0)}


def test_LastSeenBy_MultipleInstruments(tmp_path):
    csv_file = tmp_path / "tidy.csv"
    csv_file.write_text(
        "Instrument,Start Time\n"
        "STAR1,2024-01-01 08:00:00\n"
        "STAR2,2024-02-01 08:00:00\n",
        encoding="utf-8",
    )
    result = _last_seen_by_instrument(csv_file)
    assert result == {
        "STAR1": datetime(2024, 1, 1, 8, 0, 0),
        "STAR2": datetime(2024, 2, 1, 8, 0, 0),
    }


def test_last_seen_ignores_blank_instrument_and_bad_timestamps(tmp_path):
    csv_file = tmp_path / "tidy.csv"
    csv_file.write_text(
        "Instrument,Start Time\n"
        ",2024-01-01 08:00:00\n"
        "STAR1,not-a-date\n"
        "STAR1,\n",
        encoding="utf-8",
    )
    assert _last_seen_by_instrument(csv_file) == {}


def test_last_seen_empty_csv_returns_empty_dict(tmp_path):
    csv_file = tmp_path / "tidy.csv"
    csv_file.write_text("Instrument,Start Time\n", encoding="utf-8")
    assert _last_seen_by_instrument(csv_file) == {}


# =========================================================================
# _instrument_dirs
# =========================================================================

def test_instrument_dirs_excludes_processed_folder(tmp_path):
    log_folder = tmp_path
    (log_folder / "STAR1").mkdir()
    (log_folder / "STAR2").mkdir()
    processed = log_folder / "Processed"
    processed.mkdir()

    result = _instrument_dirs(log_folder, processed)
    assert {p.name for p in result} == {"STAR1", "STAR2"}


def test_instrument_dirs_excludes_files(tmp_path):
    log_folder = tmp_path
    (log_folder / "STAR1").mkdir()
    (log_folder / "notes.txt").write_text("hi", encoding="utf-8")
    processed = log_folder / "Processed"
    processed.mkdir()

    result = _instrument_dirs(log_folder, processed)
    assert {p.name for p in result} == {"STAR1"}


def test_instrument_dirs_empty_when_only_processed_exists(tmp_path):
    log_folder = tmp_path
    processed = log_folder / "Processed"
    processed.mkdir()

    assert _instrument_dirs(log_folder, processed) == []


# =========================================================================
# _find_stale
# =========================================================================

def test_find_stale_never_seen_instrument(tmp_path):
    (tmp_path / "STAR1").mkdir()
    dirs = _instrument_dirs(tmp_path, tmp_path / "Processed")
    cutoff = datetime(2024, 1, 1)

    result = _find_stale(dirs, last_seen={}, cutoff=cutoff)
    assert result == [("STAR1", None)]


def test_find_stale_seen_before_cutoff(tmp_path):
    (tmp_path / "STAR1").mkdir()
    dirs = _instrument_dirs(tmp_path, tmp_path / "Processed")
    last_seen = {"STAR1": datetime(2023, 1, 1)}
    cutoff = datetime(2024, 1, 1)

    result = _find_stale(dirs, last_seen, cutoff)
    assert result == [("STAR1", datetime(2023, 1, 1))]


def test_find_stale_recently_seen_instrument_not_stale(tmp_path):
    (tmp_path / "STAR1").mkdir()
    dirs = _instrument_dirs(tmp_path, tmp_path / "Processed")
    last_seen = {"STAR1": datetime(2024, 6, 1)}
    cutoff = datetime(2024, 1, 1)

    result = _find_stale(dirs, last_seen, cutoff)
    assert result == []


def test_find_stale_mixed_instruments(tmp_path):
    (tmp_path / "FRESH").mkdir()
    (tmp_path / "STALE").mkdir()
    dirs = _instrument_dirs(tmp_path, tmp_path / "Processed")
    last_seen = {
        "FRESH": datetime(2024, 6, 1),
        "STALE": datetime(2023, 1, 1),
    }
    cutoff = datetime(2024, 1, 1)

    result = _find_stale(dirs, last_seen, cutoff)
    assert result == [("STALE", datetime(2023, 1, 1))]


# =========================================================================
# _format_warning_line
# =========================================================================

def test_format_warning_line_with_last_seen():
    line = _format_warning_line("STAR1", datetime(2024, 1, 15, 9, 0, 0))
    assert line == "Serial: STAR1 - last seen 2024-01-15"


def test_format_warning_line_never_seen():
    line = _format_warning_line("STAR1", None)
    assert line == "Serial: STAR1 - no activity on record"


# =========================================================================
# _write_warning_file / _clear_warning_file
# =========================================================================

def test_write_warning_file_contents(tmp_path, logger):
    warning_file = tmp_path / "warning.txt"
    stale = [("STAR1", datetime(2024, 1, 1)), ("STAR2", None)]

    _write_warning_file(warning_file, stale, stale_days=45, logger=logger)

    text = warning_file.read_text(encoding="utf-8")
    assert "not reported activity in over 45 days" in text
    assert "Serial: STAR1 - last seen 2024-01-01" in text
    assert "Serial: STAR2 - no activity on record" in text
    assert not [lvl for lvl, _ in logger.messages if lvl == "ERROR"]


def test_write_warning_file_handles_oserror(tmp_path, logger):
    # Point at a path whose parent doesn't exist so write_text raises OSError
    warning_file = tmp_path / "missing_dir" / "warning.txt"

    _write_warning_file(warning_file, [("STAR1", None)], stale_days=45, logger=logger)

    error_messages = [lvl for lvl, _ in logger.messages if lvl == "ERROR"]
    assert len(error_messages) == 1


def test_clear_warning_file_removes_existing_file(tmp_path, logger):
    warning_file = tmp_path / "warning.txt"
    warning_file.write_text("stale", encoding="utf-8")

    _clear_warning_file(warning_file, logger)

    assert not warning_file.exists()
    assert any(lvl == "INFO" for lvl, _ in logger.messages)


def test_clear_warning_file_noop_when_absent(tmp_path, logger):
    warning_file = tmp_path / "warning.txt"

    _clear_warning_file(warning_file, logger)

    assert not logger.messages


# =========================================================================
# check_stale_instruments (integration)
# =========================================================================

def _make_config(tmp_path, stale_days=45):
    tidy_csv = tmp_path / "tidy.csv"
    log_folder = tmp_path
    processed_folder = tmp_path / "Processed"
    warning_file = tmp_path / "stale_instruments.txt"
    processed_folder.mkdir()
    return StaleCheckConfig(
        tidy_csv=tidy_csv,
        log_folder=log_folder,
        processed_folder=processed_folder,
        warning_file=warning_file,
        stale_days=stale_days,
    )


def test_check_stale_instruments_writes_warning_for_stale_instrument(tmp_path, logger):
    cfg = _make_config(tmp_path)
    (cfg.log_folder / "OLD_STAR").mkdir()
    old_time = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d %H:%M:%S")
    cfg.tidy_csv.write_text(f"Instrument,Start Time\nOLD_STAR,{old_time}\n", encoding="utf-8")

    check_stale_instruments(cfg, logger)

    assert cfg.warning_file.exists()
    assert "OLD_STAR" in cfg.warning_file.read_text(encoding="utf-8")
    assert logger.has_warning_containing("OLD_STAR")


def test_check_stale_instruments_clears_warning_when_all_active(tmp_path, logger):
    cfg = _make_config(tmp_path)
    (cfg.log_folder / "ACTIVE_STAR").mkdir()
    recent_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cfg.tidy_csv.write_text(f"Instrument,Start Time\nACTIVE_STAR,{recent_time}\n", encoding="utf-8")
    cfg.warning_file.write_text("stale from a previous run", encoding="utf-8")

    check_stale_instruments(cfg, logger)

    assert not cfg.warning_file.exists()
    assert not any(lvl == "WARNING" for lvl, _ in logger.messages)


def test_check_stale_instruments_no_instrument_folders(tmp_path, logger):
    cfg = _make_config(tmp_path)
    cfg.tidy_csv.write_text("Instrument,Start Time\n", encoding="utf-8")

    check_stale_instruments(cfg, logger)

    assert not cfg.warning_file.exists()
    assert not any(lvl == "WARNING" for lvl, _ in logger.messages)