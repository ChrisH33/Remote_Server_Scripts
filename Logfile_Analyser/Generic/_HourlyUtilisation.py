import logging
import sys
from pathlib import Path

import pandas as pd

# =========================================================================
# CORE CALCULATION
# =========================================================================

def calculate_hourly_utilisation(
    df: pd.DataFrame,
    days: int,
    *,
    include_idle_instruments: bool = False,
) -> pd.DataFrame:
    """
    Given a tidy logs DataFrame with 'Instrument', 'Start Time', 'End Time'
    columns, return one row per (instrument, hour) over the trailing
    `days` days, with minutes run and utilisation as a fraction of 60.
    """

    # Convert timestamps
    df["Start Time"] = pd.to_datetime(df["Start Time"], errors="coerce")
    df["End Time"] = pd.to_datetime(df["End Time"], errors="coerce")

    # Remove rows where timestamps could not be parsed
    df = df.dropna(subset=["Start Time", "End Time"])

    # Ignore invalid runs
    df = df[df["End Time"] > df["Start Time"]]

    if df.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # Define analysis period
    # --------------------------------------------------------

    latest_time = df["End Time"].max()

    end_date = latest_time.floor("D")
    start_date = end_date - pd.Timedelta(days=days - 1)

    analysis_start = start_date
    analysis_end = end_date + pd.Timedelta(days=1)

    # Keep the full instrument list before filtering to the window, in
    # case the caller wants idle instruments included as 0% rows.
    all_instruments = sorted(df["Instrument"].dropna().unique())

    # Restrict runs to anything overlapping the analysis period
    df = df[
        (df["End Time"] > analysis_start) &
        (df["Start Time"] < analysis_end)
    ].copy()

    # --------------------------------------------------------
    # Get instruments to include in the scaffold
    # --------------------------------------------------------

    if include_idle_instruments:
        instruments = all_instruments
    else:
        instruments = sorted(df["Instrument"].dropna().unique())

    if not instruments:
        return pd.DataFrame()

    # --------------------------------------------------------
    # Create complete hourly scaffold
    # --------------------------------------------------------

    hours = pd.date_range(
        start=analysis_start,
        end=analysis_end - pd.Timedelta(hours=1),
        freq="h"
    )

    scaffold = pd.MultiIndex.from_product(
        [instruments, hours],
        names=["Instrument", "Hour Start"]
    ).to_frame(index=False)

    # --------------------------------------------------------
    # Calculate overlap between every run and every hour
    # --------------------------------------------------------

    utilisation = []

    for _, run in df.iterrows():

        instrument = run["Instrument"]
        run_start = max(run["Start Time"], analysis_start)
        run_end = min(run["End Time"], analysis_end)

        # First hour touched by the run
        hour = run_start.floor("h")

        while hour < run_end:

            hour_end = hour + pd.Timedelta(hours=1)

            overlap_start = max(run_start, hour)
            overlap_end = min(run_end, hour_end)

            overlap_minutes = (
                overlap_end - overlap_start
            ).total_seconds() / 60

            if overlap_minutes > 0:
                utilisation.append({
                    "Instrument": instrument,
                    "Hour Start": hour,
                    "Run Minutes": overlap_minutes
                })

            hour += pd.Timedelta(hours=1)

    # --------------------------------------------------------
    # Aggregate runs occurring in the same hour
    # --------------------------------------------------------

    if utilisation:
        utilisation_df = pd.DataFrame(utilisation)

        utilisation_df = (
            utilisation_df
            .groupby(
                ["Instrument", "Hour Start"],
                as_index=False
            )["Run Minutes"]
            .sum()
        )

        scaffold = scaffold.merge(
            utilisation_df,
            on=["Instrument", "Hour Start"],
            how="left"
        )
    else:
        scaffold["Run Minutes"] = 0

    scaffold["Run Minutes"] = scaffold["Run Minutes"].fillna(0)

    # Don't allow an hour to exceed 60 minutes
    scaffold["Run Minutes"] = scaffold["Run Minutes"].clip(upper=60)

    # --------------------------------------------------------
    # Calculate utilisation
    # --------------------------------------------------------

    scaffold["Available Minutes"] = 60

    scaffold["Utilisation"] = (
        scaffold["Run Minutes"] /
        scaffold["Available Minutes"]
    )

    # Useful display fields
    scaffold["Date"] = scaffold["Hour Start"].dt.date
    scaffold["Hour"] = scaffold["Hour Start"].dt.hour

    return scaffold[
        [
            "Instrument",
            "Date",
            "Hour",
            "Hour Start",
            "Run Minutes",
            "Available Minutes",
            "Utilisation",
        ]
    ]

# =========================================================================
# PIPELINE ENTRY POINT (matches the style of _CleanRawLogfiles.run_cleaner,
# _CheckHistoricLogs.check_stale_instruments, etc.)
# =========================================================================

def run_hourly_utilisation(
    *,
    tidy_input_file: Path,
    output_file: Path,
    days: int,
    logger: logging.Logger,
    include_idle_instruments: bool = False,
) -> None:

    try:
        df = pd.read_csv(tidy_input_file)
    except Exception:
        logger.exception(f"Failed to read {tidy_input_file}")
        return

    required_cols = {"Instrument", "Start Time", "End Time"}
    missing = required_cols - set(df.columns)
    if missing:
        logger.error(
            f"Tidy CSV is missing required column(s): {sorted(missing)}. "
            f"Found columns: {list(df.columns)}"
        )
        return

    try:
        result = calculate_hourly_utilisation(
            df,
            days,
            include_idle_instruments=include_idle_instruments,
        )
    except Exception:
        logger.exception("Failed to calculate hourly utilisation")
        return

    if result.empty:
        logger.warning(
            f"No utilisation data produced - no valid runs found in the "
            f"trailing {days} day(s)."
        )
        return

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_file, index=False)
    except OSError:
        logger.exception(f"Failed to write {output_file}")
        return

    logger.info(
        f"Wrote hourly utilisation for {result['Instrument'].nunique()} "
        f"instrument(s) across {days} day(s) "
        f"({len(result)} rows) to {output_file}"
    )