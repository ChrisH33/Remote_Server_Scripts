"""
Tests for Logfile_Analyser/Generic/_HourlyUtilisation.py

calc_hourly_util() is pure - it takes a DataFrame in and returns a
DataFrame out, with no file I/O - so it's the easiest and most valuable
thing in this module to test. run_hourly_utilisation() is the thin
CSV-in/CSV-out wrapper around it and gets a couple of higher-level tests
using tmp_path.
"""
import pandas as pd
import pytest

from Logfile_Analyser.Generic._HourlyUtilisation import (
    calc_hourly_util,
    run_hourly_utilisation,
)


def make_runs(rows: list[dict]) -> pd.DataFrame:
    """
    Build a minimal tidy-CSV-shaped DataFrame from a list of
    {"Instrument": ..., "Start Time": ..., "End Time": ...} dicts.
    """
    return pd.DataFrame(rows)


# -------------------------------------------------------------------
# Basic single-run cases
# -------------------------------------------------------------------

def test_run_entirely_within_one_hour():
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-01 10:15:00", "End Time": "2024-01-01 10:45:00"},
    ])

    result = calc_hourly_util(df, days=1)

    hour_row = result[(result["Instrument"] == "Bravo-1") & (result["Hour"] == 10)]
    assert len(hour_row) == 1
    assert hour_row["Run Minutes"].iloc[0] == pytest.approx(30)
    assert hour_row["Utilisation"].iloc[0] == pytest.approx(0.5)
    assert hour_row["Available Minutes"].iloc[0] == 60

    # every other hour for this instrument should be zero, not missing
    other_hours = result[(result["Instrument"] == "Bravo-1") & (result["Hour"] != 10)]
    assert (other_hours["Run Minutes"] == 0).all()


def test_run_spanning_an_hour_boundary_splits_correctly():
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-01 09:45:00", "End Time": "2024-01-01 10:15:00"},
    ])

    result = calc_hourly_util(df, days=1)

    hour_9 = result[(result["Instrument"] == "Bravo-1") & (result["Hour"] == 9)]
    hour_10 = result[(result["Instrument"] == "Bravo-1") & (result["Hour"] == 10)]

    assert hour_9["Run Minutes"].iloc[0] == pytest.approx(15)
    assert hour_10["Run Minutes"].iloc[0] == pytest.approx(15)


def test_run_spanning_multiple_hours():
    # 2 hours 10 minutes, starting mid-hour: 09:50 -> 12:00
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-01 09:50:00", "End Time": "2024-01-01 12:00:00"},
    ])

    result = calc_hourly_util(df, days=1)
    subset = result[result["Instrument"] == "Bravo-1"].set_index("Hour")

    assert subset.loc[9, "Run Minutes"] == pytest.approx(10)
    assert subset.loc[10, "Run Minutes"] == pytest.approx(60)
    assert subset.loc[11, "Run Minutes"] == pytest.approx(60)
    # total run time should equal 130 minutes across all touched hours
    assert subset.loc[[9, 10, 11], "Run Minutes"].sum() == pytest.approx(130)


# -------------------------------------------------------------------
# Overlapping / back-to-back runs and the 60-minute clip
# -------------------------------------------------------------------

def test_run_minutes_are_clipped_to_60_per_hour():
    # Two runs that both land in the 10:00 hour and together exceed 60
    # minutes (e.g. overlapping runs, or a logging glitch). The pipeline
    # should never report more than 60 "used" minutes in a 60 minute hour.
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-01 10:00:00", "End Time": "2024-01-01 10:50:00"},
        {"Instrument": "Bravo-1", "Start Time": "2024-01-01 10:10:00", "End Time": "2024-01-01 10:55:00"},
    ])

    result = calc_hourly_util(df, days=1)
    hour_10 = result[(result["Instrument"] == "Bravo-1") & (result["Hour"] == 10)]

    assert hour_10["Run Minutes"].iloc[0] == 60
    assert hour_10["Utilisation"].iloc[0] == 1.0


# -------------------------------------------------------------------
# Multiple instruments / idle instruments
# -------------------------------------------------------------------

def test_idle_instrument_excluded_by_default():
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-01 10:00:00", "End Time": "2024-01-01 10:30:00"},
    ])

    result = calc_hourly_util(df, days=1, include_idle_instruments=False)

    assert set(result["Instrument"].unique()) == {"Bravo-1"}


def test_include_idle_instruments_adds_zero_rows():
    # Bravo-2's only run is 10 days before the analysis window (given
    # days=1 anchored on Bravo-1's run), so within the window it's idle.
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-10 10:00:00", "End Time": "2024-01-10 10:30:00"},
        {"Instrument": "Bravo-2", "Start Time": "2024-01-01 10:00:00", "End Time": "2024-01-01 10:30:00"},
    ])

    without_idle = calc_hourly_util(df, days=1, include_idle_instruments=False)
    assert "Bravo-2" not in set(without_idle["Instrument"].unique())

    with_idle = calc_hourly_util(df, days=1, include_idle_instruments=True)
    assert "Bravo-2" in set(with_idle["Instrument"].unique())
    bravo_2_rows = with_idle[with_idle["Instrument"] == "Bravo-2"]
    assert (bravo_2_rows["Run Minutes"] == 0).all()


# -------------------------------------------------------------------
# Window handling / days parameter
# -------------------------------------------------------------------

def test_days_window_excludes_older_runs():
    # Latest run anchors the window. A run 10 days before that should be
    # excluded from a 1-day window.
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-10 10:00:00", "End Time": "2024-01-10 10:30:00"},
        {"Instrument": "Bravo-1", "Start Time": "2023-12-31 10:00:00", "End Time": "2023-12-31 10:30:00"},
    ])

    result = calc_hourly_util(df, days=1)
    dates_present = set(result["Date"].astype(str))
    assert dates_present == {"2024-01-10"}


def test_days_window_includes_older_runs_when_within_range():
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-10 10:00:00", "End Time": "2024-01-10 10:30:00"},
        {"Instrument": "Bravo-1", "Start Time": "2024-01-08 10:00:00", "End Time": "2024-01-08 10:30:00"},
    ])

    result = calc_hourly_util(df, days=3)  # covers 8th, 9th, 10th
    dates_present = set(result["Date"].astype(str))
    assert dates_present == {"2024-01-08", "2024-01-09", "2024-01-10"}


# -------------------------------------------------------------------
# Edge cases: bad / missing data
# -------------------------------------------------------------------

def test_empty_dataframe_returns_empty():
    df = make_runs([])
    # calc_hourly_util expects the columns to exist even if there are no rows
    df = pd.DataFrame(columns=["Instrument", "Start Time", "End Time"])
    result = calc_hourly_util(df, days=1)
    assert result.empty


def test_unparseable_timestamps_are_dropped_not_raised():
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "not-a-date", "End Time": "also-not-a-date"},
    ])
    result = calc_hourly_util(df, days=1)
    assert result.empty


def test_end_before_start_is_ignored():
    df = make_runs([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-01 11:00:00", "End Time": "2024-01-01 10:00:00"},
    ])
    result = calc_hourly_util(df, days=1)
    assert result.empty


# -------------------------------------------------------------------
# run_hourly_utilisation() - the CSV-in/CSV-out wrapper
# -------------------------------------------------------------------

def test_run_hourly_utilisation_writes_csv(tmp_path, logger):
    summary_file = tmp_path / "TidyLogs_ForTableau.csv"
    output_file = tmp_path / "InstrumentUtilisation.csv"

    pd.DataFrame([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-01 10:00:00", "End Time": "2024-01-01 10:30:00"},
    ]).to_csv(summary_file, index=False)

    run_hourly_utilisation(
        summary_file=summary_file,
        output_file=output_file,
        days=1,
        exclude_weekends=False,
        logger=logger,
    )

    assert output_file.exists()
    written = pd.read_csv(output_file)
    assert "Bravo-1" in written["Instrument"].values


def test_run_hourly_utilisation_missing_summary_file_logs_and_returns(tmp_path, logger):
    run_hourly_utilisation(
        summary_file=tmp_path / "does_not_exist.csv",
        output_file=tmp_path / "out.csv",
        days=1,
        exclude_weekends=False,
        logger=logger,
    )
    assert not (tmp_path / "out.csv").exists()
    assert any(level == "EXCEPTION" for level, _ in logger.messages)


def test_exclude_weekends_drops_saturday_and_sunday(tmp_path, logger):
    summary_file = tmp_path / "TidyLogs_ForTableau.csv"
    output_file = tmp_path / "InstrumentUtilisation.csv"

    # 2024-01-06 is a Saturday, 2024-01-08 is a Monday
    pd.DataFrame([
        {"Instrument": "Bravo-1", "Start Time": "2024-01-06 10:00:00", "End Time": "2024-01-06 10:30:00"},
        {"Instrument": "Bravo-1", "Start Time": "2024-01-08 10:00:00", "End Time": "2024-01-08 10:30:00"},
    ]).to_csv(summary_file, index=False)

    run_hourly_utilisation(
        summary_file=summary_file,
        output_file=output_file,
        days=3,
        exclude_weekends=True,
        logger=logger,
    )

    written = pd.read_csv(output_file)
    assert "2024-01-06" not in written["Date"].astype(str).values
    assert "2024-01-08" in written["Date"].astype(str).values