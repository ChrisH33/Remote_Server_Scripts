"""
Tests for Logfile_Analyser/Generic/_CleanRawLogfiles.py

Most of the value here is in the small pure helper functions
(parse_datetime, calculate_run_duration, extract_process_type_and_method)
plus clean_row(), which stitches them together and applies the
drop-rules. run_cleaner() itself does file I/O and dedupe against an
existing tidy CSV, so it gets a couple of tmp_path tests too.
"""
from datetime import datetime
from typing import cast

from Logfile_Analyser.Generic._CleanRawLogfiles import (
    parse_datetime,
    calculate_run_duration,
    extract_run_date,
    extract_process_type_and_method,
    clean_row,
    run_cleaner,
)

# A tiny process_types dict in the same shape as Main_Config.PROCESS_TYPES,
# so these tests don't depend on the (huge, ever-changing) real one.
PROCESS_TYPES = {
    "Clean Up": {
        "Generic_SPRI_CleanUp": ["GENERIC_SPRI_CLEANUP", "GENERIC_BEAD_CLEANUP"],
    },
    "Pooling": {
        "PoolSample": ["POOLSAMPLE_V1", "POOLSAMPLE_V2"],
    },
}

TIDY_FIELDS = [
    ("instrument", "Instrument", "text"),
    ("filename", "Filename", "text"),
    ("start_time", "Start Time", "datetime"),
    ("end_time", "End Time", "datetime"),
    ("status", "Status", "text"),
    ("sim_mode", "Sim Mode", "text"),
    ("method", "Method", "text"),
    ("run_duration_minutes", "Run Duration (min)", "float"),
    ("run_date", "Run Date", "date"),
    ("process_type", "Process Type", "text"),
    ("method_simplified", "Method Simp.", "text"),
]


# -------------------------------------------------------------------
# parse_datetime
# -------------------------------------------------------------------

def test_parse_datetime_accepts_iso_format(logger):
    result = parse_datetime("2023-10-17 14:10:00", logger)
    assert result == datetime(2023, 10, 17, 14, 10, 0)


def test_parse_datetime_accepts_day_first_format(logger):
    result = parse_datetime("17/10/2023 14:10", logger)
    assert result == datetime(2023, 10, 17, 14, 10)


def test_parse_datetime_returns_none_and_warns_on_garbage(logger):
    result = parse_datetime("not a date", logger)
    assert result is None
    assert logger.has_warning_containing("Could not parse")


def test_parse_datetime_returns_none_and_warns_on_missing_value(logger):
    assert parse_datetime(cast(str, None), logger) is None
    assert parse_datetime("", logger) is None
    assert parse_datetime("   ", logger) is None
    assert logger.has_warning_containing("Missing datetime value")


# -------------------------------------------------------------------
# calculate_run_duration / extract_run_date
# -------------------------------------------------------------------

def test_calculate_run_duration_normal_case():
    start = datetime(2023, 10, 17, 14, 0, 0)
    end = datetime(2023, 10, 17, 14, 30, 0)
    assert calculate_run_duration(start, end) == 30.0


def test_calculate_run_duration_missing_times_returns_empty_string():
    assert calculate_run_duration(None, datetime(2023, 10, 17)) == ""
    assert calculate_run_duration(datetime(2023, 10, 17), None) == ""
    assert calculate_run_duration(None, None) == ""


def test_extract_run_date_formats_as_iso():
    assert extract_run_date(datetime(2023, 10, 17, 14, 0, 0)) == "2023-10-17"


def test_extract_run_date_handles_none():
    assert extract_run_date(None) == ""


# -------------------------------------------------------------------
# extract_process_type_and_method
# -------------------------------------------------------------------

def test_extract_process_type_matches_known_method(logger):
    process_type, simplified = extract_process_type_and_method(
        "generic_spri_cleanup", PROCESS_TYPES, logger
    )
    assert process_type == "Clean Up"
    assert simplified == "Generic_SPRI_CleanUp"


def test_extract_process_type_is_case_insensitive(logger):
    process_type, simplified = extract_process_type_and_method(
        "PoolSample_V1", PROCESS_TYPES, logger
    )
    assert process_type == "Pooling"
    assert simplified == "PoolSample"


def test_extract_process_type_unknown_method(logger):
    process_type, simplified = extract_process_type_and_method(
        "SOME_UNLISTED_METHOD", PROCESS_TYPES, logger
    )
    assert process_type == "Unknown"
    assert simplified == "Unknown"


def test_extract_process_type_handles_non_string_method(logger):
    # e.g. a NaN from pandas for a blank Method column
    process_type, simplified = extract_process_type_and_method(
        cast(str, float("nan")), PROCESS_TYPES, logger
    )
    assert process_type == "Unknown"
    assert simplified == "Unknown"
    assert logger.has_warning_containing("Invalid method")


# -------------------------------------------------------------------
# clean_row
# -------------------------------------------------------------------

def _raw_row(**overrides):
    row = {
        "Instrument": "Bravo-1",
        "Filename": "some_logfile.log",
        "Start Time": "2023-10-17 14:00:00",
        "End Time": "2023-10-17 14:30:00",
        "Status": "Complete",
        "Sim Mode": "Live",
        "Method": "GENERIC_SPRI_CLEANUP",
    }
    row.update(overrides)
    return row


def test_clean_row_produces_expected_tidy_row(logger):
    row = clean_row(
        _raw_row(),
        statuses_to_drop={"Read Error", "No Start Found"},
        filename_prefixes_to_drop=("vworks_pipette_log",),
        process_types=PROCESS_TYPES,
        tidy_fields=TIDY_FIELDS,
        logger=logger,
    )

    assert row is not None
    tidy = dict(zip([f[0] for f in TIDY_FIELDS], row))
    assert tidy["instrument"] == "Bravo-1"
    assert tidy["status"] == "complete"
    assert tidy["run_duration_minutes"] == 30.0
    assert tidy["run_date"] == "2023-10-17"
    assert tidy["process_type"] == "Clean Up"
    assert tidy["method_simplified"] == "Generic_SPRI_CleanUp"


def test_clean_row_drops_unwanted_status(logger):
    row = clean_row(
        _raw_row(Status="Read Error"),
        statuses_to_drop={"Read Error", "No Start Found"},
        filename_prefixes_to_drop=(),
        process_types=PROCESS_TYPES,
        tidy_fields=TIDY_FIELDS,
        logger=logger,
    )
    assert row is None


def test_clean_row_drops_unwanted_filename_prefix(logger):
    row = clean_row(
        _raw_row(Filename="VWorks_Pipette_Log_2023.log"),
        statuses_to_drop=set(),
        filename_prefixes_to_drop=("vworks_pipette_log",),
        process_types=PROCESS_TYPES,
        tidy_fields=TIDY_FIELDS,
        logger=logger,
    )
    assert row is None


# -------------------------------------------------------------------
# run_cleaner - file I/O + dedupe
# -------------------------------------------------------------------

def test_run_cleaner_writes_tidy_rows_and_skips_existing_ids(tmp_path, logger):
    raw_csv = tmp_path / "CondensedLogs_Raw.csv"
    tidy_csv = tmp_path / "TidyLogs_ForTableau.csv"

    # NB: run_cleaner dedupes on column index 1 (the second column), which
    # is "Filename" in the raw FIELDS layout used by MainScript/ParseLogs.
    raw_csv.write_text(
        "Instrument,Filename,Start Time,End Time,Status,Sim Mode,Method\n"
        "Bravo-1,run_1.log,2023-10-17 14:00:00,2023-10-17 14:30:00,Complete,Live,GENERIC_SPRI_CLEANUP\n"
        "Bravo-1,run_2.log,2023-10-18 09:00:00,2023-10-18 09:15:00,Complete,Live,POOLSAMPLE_V1\n",
        encoding="utf-8",
    )

    run_cleaner(
        raw_input_file=raw_csv,
        tidy_output_file=tidy_csv,
        tidy_fields=TIDY_FIELDS,
        statuses_to_drop={"Read Error", "No Start Found"},
        filename_prefixes_to_drop=(),
        process_types=PROCESS_TYPES,
        logger=logger,
    )

    assert tidy_csv.exists()
    import pandas as pd
    tidy = pd.read_csv(tidy_csv)
    assert len(tidy) == 2
    assert set(tidy["Filename"]) == {"run_1.log", "run_2.log"}

    # Running again with the same raw data should add nothing new
    run_cleaner(
        raw_input_file=raw_csv,
        tidy_output_file=tidy_csv,
        tidy_fields=TIDY_FIELDS,
        statuses_to_drop={"Read Error", "No Start Found"},
        filename_prefixes_to_drop=(),
        process_types=PROCESS_TYPES,
        logger=logger,
    )
    tidy_after = pd.read_csv(tidy_csv)
    assert len(tidy_after) == 2