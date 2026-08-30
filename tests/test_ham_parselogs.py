"""
Tests for Logfile_Analyser/Hamilton/Ham_ParseLogs.py
"""
from pathlib import Path
from datetime import datetime, timedelta
from Logfile_Analyser.Hamilton.Ham_ParseLogs import (
    parse_timestamp,
    parse_method_name,
    parse_status,
    parse_simulation_mode,
    process_file,
    write_results,
    run_parser
)
from Logfile_Analyser._ProcessTypes import FIELDS


# =========================================================================
# Parse TimeStamp
# =========================================================================

def test_ParseTimestamp_Valid():
    line = "2023-10-17 14:10:00 some trailing text after the first 19 chars"
    assert parse_timestamp(line) == datetime(2023, 10, 17, 14, 10, 0)

def test_ParseTimestamp_EmptyString():
    assert parse_timestamp("") is None

def test_ParseTimestamp_Malformed():
    line = "13/14/2024 01:63:14 and some training txt after my string"
    assert parse_timestamp(line) is None

# =========================================================================
# Parse Method Name
# =========================================================================

def test_ParseMethod_Valid():
    line = r"Method file C:\Program Files (x86)\HAMILTON\Methods\SangerCleanup\Methods\SangerCleanup_TemplateOnly\SangerCleanupTemplateOnly.hsl"
    assert parse_method_name(line) == "SangerCleanupTemplateOnly"

def test_ParseMethod_EmptyString():
    assert parse_method_name("") is None

def test_ParseMethod_Malformed():
    line = r"Method C:\Program Files (x86)\HAMILTON\Methods\SangerCleanup\Methods\SangerCleanup_TemplateOnly\SangerCleanupTemplateOnly.hsl"
    assert parse_method_name(line) is None

# =========================================================================
# Parse Status
# =========================================================================

def test_ParseStatus_ValidComplete():
    line = "2026-08-17 15:18:59> SYSTEM : End method - start; "
    assert parse_status(line) == "Complete"

def test_ParseStatus_ValidAbort():
    line = "2026-08-17 15:18:59> SYSTEM : Abort Method - start; "
    assert parse_status(line) is "Aborted"

# =========================================================================
# Parse Simulation Mode
# =========================================================================

def test_ParseSimulation_Valid():
    line = "Start method command - progress; Serial number of Instrument: 0000"
    assert parse_simulation_mode(line) is "Sim"

def test_ParseSimulation_EmptyString():
    assert parse_simulation_mode("") is None

def test_ParseSimulation_Malformed():
    line = "Start method command - progress; Asset number of Instrument: 0000"
    assert parse_simulation_mode(line) is None

# =========================================================================
# Process File
# =========================================================================

# =========================================================================
# Write Results
# =========================================================================

# =========================================================================
# Run Parser
# =========================================================================



def _write_trc(tmp_path: Path, instrument: str, lines: list[str]) -> Path:
    instrument_dir = tmp_path / instrument
    instrument_dir.mkdir(parents=True, exist_ok=True)
    logfile = instrument_dir / "run.trc"
    logfile.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return logfile


def test_process_file_complete_run_sim_mode(tmp_path):
    logfile = _write_trc(tmp_path, "Hamilton-1", [
        "2023-10-17 14:00:00 STAR : Start method command - Progress; Serial number of instrument: 0000",
        "2023-10-17 14:00:01 System : Analyze method - Start; method file C:\\Methods\\MyMethod.hsl",
        "2023-10-17 14:00:02 System : Start method - Complete;",
        "2023-10-17 14:29:58 filler line one",
        "2023-10-17 14:29:59 filler line two",
        "2023-10-17 14:30:00 System : End method - Start;",
    ])

    result = process_file(logfile, fields=FIELDS)
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


def test_process_file_live_mode_from_nonzero_serial(tmp_path):
    logfile = _write_trc(tmp_path, "Hamilton-1", [
        "2023-10-17 14:00:00 STAR : Start method command - Progress; Serial number of instrument: 1234",
        "2023-10-17 14:00:02 System : Start method - Complete;",
        "2023-10-17 14:29:59 filler",
        "2023-10-17 14:30:00 System : End method - Start;",
    ])

    result = process_file(logfile, fields=FIELDS)
    assert result is not None
    _, row = result
    row_data = dict(zip([key for key, _ in FIELDS], row))
    assert row_data["sim_mode"] == "Live"


def test_process_file_no_start_found(tmp_path):
    logfile = _write_trc(tmp_path, "Hamilton-1", [
        "2023-10-17 14:00:00 nothing relevant happens here",
    ])

    result = process_file(logfile, fields=FIELDS)
    assert result is not None
    _, row = result
    row_data = dict(zip([key for key, _ in FIELDS], row))
    assert row_data["status"] == "No Start Found"
    assert row_data["start_time"] is None


def test_process_file_incomplete_run(tmp_path):
    logfile = _write_trc(tmp_path, "Hamilton-1", [
        "2023-10-17 14:00:00 System : Start method - Complete;",
        "2023-10-17 14:05:00 still running, no end or abort event ever appears",
    ])

    result = process_file(logfile, fields=FIELDS)
    assert result is not None
    _, row = result
    row_data = dict(zip([key for key, _ in FIELDS], row))
    assert row_data["status"] == "Incomplete"