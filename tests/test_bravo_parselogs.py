"""
Tests for Logfile_Analyser/Bravo/Bravo_ParseLogs.py

parse_bravo_file() reads real .log files line by line, so these tests
write small synthetic log files to tmp_path rather than mocking the
file handle - it's a more faithful test and much less fragile than
patching `open`.
"""
from pathlib import Path

from Logfile_Analyser.Bravo.Bravo_ParseLogs import (
    extract_timestamp,
    extract_method,
    parse_bravo_file,
)


# -------------------------------------------------------------------
# parse_timestamp
# -------------------------------------------------------------------

def test_parse_timestamp_accepts_slash_format():
    result = extract_timestamp("17/10/2023 14:10:00")
    assert result is not None
    assert (result.year, result.month, result.day, result.hour, result.minute) == (2023, 10, 17, 14, 10)


def test_parse_timestamp_accepts_dash_format():
    result = extract_timestamp("17-Oct-23 02:10:00 PM")
    assert result is not None
    assert (result.year, result.month, result.day, result.hour, result.minute) == (2023, 10, 17, 14, 10)


def test_parse_timestamp_returns_none_for_garbage():
    assert extract_timestamp("garbage") is None


# -------------------------------------------------------------------
# extract_method / extract_runset
# -------------------------------------------------------------------

def test_extract_method_finds_pro_filename():
    line = r"C:\Programs\Methods\CleanUpSPRI.pro	Startup protocol starting"
    assert extract_method(line) == "CleanUpSPRI.pro"


def test_extract_method_returns_none_when_absent():
    assert extract_method("No method here") is None

# -------------------------------------------------------------------
# parse_bravo_file - end-to-end over a synthetic log
# -------------------------------------------------------------------

def _write_log(tmp_path: Path, instrument: str, lines: list[str]) -> Path:
    instrument_dir = tmp_path / instrument
    instrument_dir.mkdir(parents=True, exist_ok=True)
    logfile = instrument_dir / "run.log"
    logfile.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return logfile


def test_parse_bravo_file_complete_run(tmp_path, logger):
    logfile = _write_log(tmp_path, "Bravo-1", [
        r"17/10/2023 14:00:00	Startup protocol starting	C:\Methods\CleanUpSPRI.pro",
        "17/10/2023 14:00:05\tsome intermediate step",
        "17/10/2023 14:29:55\tsome intermediate step",
        "17/10/2023 14:30:00\tMain protocol complete",
    ])

    runs = parse_bravo_file(logfile)

    assert len(runs) == 1
    run = runs[0]
    assert run.instrument == "Bravo-1"
    assert run.method == "CleanUpSPRI.pro"
    assert run.status == "Complete"
    assert run.start_time is not None
    assert run.end_time is not None
    assert run.uniqueID is not None


def test_parse_bravo_file_aborted_run(tmp_path, logger):
    logfile = _write_log(tmp_path, "Bravo-1", [
        r"17/10/2023 14:00:00	Startup protocol starting	C:\Methods\CleanUpSPRI.pro",
        "17/10/2023 14:05:00\tsome intermediate step",
        "17/10/2023 14:10:00\tMain protocol aborted by user",
    ])

    runs = parse_bravo_file(logfile)

    assert len(runs) == 1
    assert runs[0].status == "Aborted"


def test_parse_bravo_file_multiple_runs_in_one_file(tmp_path, logger):
    logfile = _write_log(tmp_path, "Bravo-1", [
        r"17/10/2023 14:00:00	Startup protocol starting	C:\Methods\CleanUpSPRI.pro",
        "17/10/2023 14:04:55\tstep",
        "17/10/2023 14:05:00\tMain protocol complete",
        r"17/10/2023 15:00:00	Startup protocol starting	C:\Methods\Pooling.pro",
        "17/10/2023 15:09:55\tstep",
        "17/10/2023 15:10:00\tMain protocol complete",
    ])

    runs = parse_bravo_file(logfile)

    assert len(runs) == 2
    assert [r.method for r in runs] == ["CleanUpSPRI.pro", "Pooling.pro"]


def test_parse_bravo_file_missing_file_returns_empty_list(tmp_path, logger):
    missing = tmp_path / "Bravo-1" / "does_not_exist.log"
    assert parse_bravo_file(missing) == []