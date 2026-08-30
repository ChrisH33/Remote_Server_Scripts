from datetime import datetime, timedelta

from Logfile_Analyser.Generic._CheckHistoricLogs import (
    delete_file,
    get_last_seen_per_instrument,
    write_stale_warning,
    check_stale_instruments,
)


# =========================================================================
# delete_file
# =========================================================================

def test_delete_file_removes_existing_file(tmp_path):
    warning_file = tmp_path / "warning.txt"
    warning_file.write_text("stale", encoding="utf-8")
    delete_file(warning_file)
    assert not warning_file.exists()

def test_delete_file_does_nothing_when_file_is_missing(tmp_path):
    warning_file = tmp_path / "warning.txt"
    delete_file(warning_file)
    assert not warning_file.exists()

# =========================================================================
# get_last_seen_per_instrument
# =========================================================================

def test_get_last_seen_per_instrument_picks_most_recent_row(tmp_path):
    csv_file = tmp_path / "tidy.csv"

    csv_file.write_text(
        "Instrument,Start Time\n"
        "STAR1,2024-01-01 08:00:00\n"
        "STAR1,2024-01-10 08:00:00\n"
        "STAR1,2024-01-05 08:00:00\n",
        encoding="utf-8",
    )

    result = get_last_seen_per_instrument(csv_file)
    assert result == {"STAR1": datetime(2024, 1, 10, 8, 0, 0)}


def test_get_last_seen_per_instrument_handles_multiple_instruments(tmp_path):
    csv_file = tmp_path / "tidy.csv"

    csv_file.write_text(
        "Instrument,Start Time\n"
        "STAR1,2024-01-01 08:00:00\n"
        "STAR2,2024-02-01 08:00:00\n",
        encoding="utf-8",
    )

    result = get_last_seen_per_instrument(csv_file)

    assert result == {
        "STAR1": datetime(2024, 1, 1, 8, 0, 0),
        "STAR2": datetime(2024, 2, 1, 8, 0, 0),
    }


def test_get_last_seen_per_instrument_ignores_blank_instrument(tmp_path):
    csv_file = tmp_path / "tidy.csv"

    csv_file.write_text(
        "Instrument,Start Time\n"
        ",2024-01-01 08:00:00\n"
        "STAR1,2024-01-02 08:00:00\n",
        encoding="utf-8",
    )

    result = get_last_seen_per_instrument(csv_file)

    assert result == {
        "STAR1": datetime(2024, 1, 2, 8, 0, 0)
    }


def test_get_last_seen_per_instrument_empty_csv(tmp_path):
    csv_file = tmp_path / "tidy.csv"

    csv_file.write_text(
        "Instrument,Start Time\n",
        encoding="utf-8",
    )

    result = get_last_seen_per_instrument(csv_file)

    assert result == {}


# =========================================================================
# write_stale_warning
# =========================================================================

def test_write_stale_warning_contents(tmp_path):
    warning_file = tmp_path / "warning.txt"

    stale = [
        ("STAR1", datetime(2024, 1, 1)),
        ("STAR2", datetime(2024, 1, 10)),
    ]

    write_stale_warning(
        warning_file,
        stale,
        stale_days=45,
    )

    text = warning_file.read_text(encoding="utf-8")

    assert "not reported activity in over 45 days" in text
    assert "Serial: STAR1 - last seen 2024-01-01" in text
    assert "Serial: STAR2 - last seen 2024-01-10" in text


def test_write_stale_warning_raises_on_oserror(tmp_path):
    warning_file = tmp_path / "missing_dir" / "warning.txt"

    stale = [
        ("STAR1", datetime(2024, 1, 1)),
    ]

    try:
        write_stale_warning(
            warning_file,
            stale,
            stale_days=45,
        )
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "Could not write warning file" in str(e)


# =========================================================================
# check_stale_instruments
# =========================================================================

def test_check_stale_instruments_writes_warning_for_stale_instrument(
    tmp_path,
    logger,
):
    tidy_csv = tmp_path / "tidy.csv"
    warning_file = tmp_path / "stale_instruments.txt"

    old_time = (
        datetime.now() - timedelta(days=100)
    ).strftime("%Y-%m-%d %H:%M:%S")

    tidy_csv.write_text(
        f"Instrument,Start Time\n"
        f"OLD_STAR,{old_time}\n",
        encoding="utf-8",
    )

    check_stale_instruments(
        tidy_csv,
        warning_file,
        logger,
    )

    assert warning_file.exists()

    text = warning_file.read_text(encoding="utf-8")

    assert "OLD_STAR" in text
    assert logger.has_warning_containing("Found 1 stale instrument")


def test_check_stale_instruments_clears_warning_when_all_active(
    tmp_path,
    logger,
):
    tidy_csv = tmp_path / "tidy.csv"
    warning_file = tmp_path / "stale_instruments.txt"

    recent_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tidy_csv.write_text(
        f"Instrument,Start Time\n"
        f"ACTIVE_STAR,{recent_time}\n",
        encoding="utf-8",
    )

    warning_file.write_text(
        "stale from a previous run",
        encoding="utf-8",
    )

    check_stale_instruments(
        tidy_csv,
        warning_file,
        logger,
    )

    assert not warning_file.exists()
    assert not any(
        level == "WARNING"
        for level, _ in logger.messages
    )


def test_check_stale_instruments_no_instrument_activity(
    tmp_path,
    logger,
):
    tidy_csv = tmp_path / "tidy.csv"
    warning_file = tmp_path / "stale_instruments.txt"

    tidy_csv.write_text(
        "Instrument,Start Time\n",
        encoding="utf-8",
    )

    check_stale_instruments(
        tidy_csv,
        warning_file,
        logger,
    )

    assert not warning_file.exists()
    assert not any(
        level == "WARNING"
        for level, _ in logger.messages
    )