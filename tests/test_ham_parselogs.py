"""
Tests for Logfile_Analyser/Hamilton/Ham_ParseLogs.py
"""
from pathlib import Path

from Logfile_Analyser.Hamilton.Ham_ParseLogs import parse_timestamp, process_file

FIELDS = [
    ("instrument", "Instrument"),
    ("filename", "Filename"),
    ("start_time", "Start Time"),
    ("end_time", "End Time"),
    ("status", "Status"),
    ("sim_mode", "Sim Mode"),
    ("method", "Method"),
]


def test_parse_timestamp_valid(logger):
    line = "2023-10-17 14:10:00 some trailing text after the first 19 chars"
    result = parse_timestamp(line, "file.trc", logger)
    assert result is not None
    assert (result.year, result.month, result.day, result.hour, result.minute, result.second) == (
        2023, 10, 17, 14, 10, 0,
    )


def test_parse_timestamp_invalid_logs_warning(logger):
    result = parse_timestamp("not a timestamp!!!", "file.trc", logger)
    assert result is None
    assert logger.has_warning_containing("Invalid timestamp")


def _write_trc(tmp_path: Path, instrument: str, lines: list[str]) -> Path:
    instrument_dir = tmp_path / instrument
    instrument_dir.mkdir(parents=True, exist_ok=True)
    logfile = instrument_dir / "run.trc"
    logfile.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return logfile


def test_process_file_complete_run_sim_mode(tmp_path, logger):
    logfile = _write_trc(tmp_path, "Hamilton-1", [
        "2023-10-17 14:00:00 STAR : Start method command - Progress; Serial number of instrument: 0000",
        "2023-10-17 14:00:01 System : Analyze method - Start; method file C:\\Methods\\MyMethod.hsl",
        "2023-10-17 14:00:02 System : Start method - Complete;",
        "2023-10-17 14:29:58 filler line one",
        "2023-10-17 14:29:59 filler line two",
        "2023-10-17 14:30:00 System : End method - Start;",
    ])

    result = process_file(logfile, logger, fields=FIELDS)
    assert result is not None
    returned_path, row = result
    assert returned_path == logfile

    row_data = dict(zip([key for key, _ in FIELDS], row))
    assert row_data["instrument"] == "Hamilton-1"
    assert row_data["status"] == "Complete"
    assert row_data["sim_mode"] == "Sim"
    assert row_data["method"] == "MyMethod"
    assert row_data["start_time"] is not None
    assert row_data["end_time"] is not None


def test_process_file_live_mode_from_nonzero_serial(tmp_path, logger):
    logfile = _write_trc(tmp_path, "Hamilton-1", [
        "2023-10-17 14:00:00 STAR : Start method command - Progress; Serial number of instrument: 1234",
        "2023-10-17 14:00:02 System : Start method - Complete;",
        "2023-10-17 14:29:59 filler",
        "2023-10-17 14:30:00 System : End method - Start;",
    ])

    result = process_file(logfile, logger, fields=FIELDS)
    assert result is not None
    _, row = result
    row_data = dict(zip([key for key, _ in FIELDS], row))
    assert row_data["sim_mode"] == "Live"


def test_process_file_no_start_found(tmp_path, logger):
    logfile = _write_trc(tmp_path, "Hamilton-1", [
        "2023-10-17 14:00:00 nothing relevant happens here",
    ])

    result = process_file(logfile, logger, fields=FIELDS)
    assert result is not None
    _, row = result
    row_data = dict(zip([key for key, _ in FIELDS], row))
    assert row_data["status"] == "No Start Found"
    assert row_data["start_time"] is None


def test_process_file_incomplete_run(tmp_path, logger):
    logfile = _write_trc(tmp_path, "Hamilton-1", [
        "2023-10-17 14:00:00 System : Start method - Complete;",
        "2023-10-17 14:05:00 still running, no end or abort event ever appears",
    ])

    result = process_file(logfile, logger, fields=FIELDS)
    assert result is not None
    _, row = result
    row_data = dict(zip([key for key, _ in FIELDS], row))
    assert row_data["status"] == "Incomplete"