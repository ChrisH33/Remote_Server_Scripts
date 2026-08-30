from typing import cast
from pathlib import Path
import pandas as pd

UTIL_FIELDS = [
    ("instrument",              "Instrument",           "text"),
    ("date",                    "Date",                 "date"),
    ("hour",                    "Hour",                 "int"),
    ("hour_start",              "Hour Start",           "datetime"),
    ("run_minutes",             "Run Minutes",          "float"),
    ("available_minutes",       "Available Minutes",    "int"),
    ("utilisation",             "Utilisation",          "float"),
]

# =========================================================================
# CORE CALCULATION
# =========================================================================

def calc_hourly_util(
    df: pd.DataFrame,
    days: int,
    *,
    include_idle_instruments: bool = False,
) -> pd.DataFrame:
    
    # Convert timestamps
    df["Start Time"] = pd.to_datetime(df["Start Time"], errors="coerce")
    df["End Time"] = pd.to_datetime(df["End Time"], errors="coerce")

    df = df.dropna(subset=["Start Time", "End Time"])   # Remove rows where timestamps could not be parsed
    df = df[df["End Time"] > df["Start Time"]]          # Ignore invalid runs
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
    all_instruments = sorted(df["Instrument"].dropna().unique()) # Get the full instrument lists

    # Restrict runs to anything overlapping the analysis period
    df = cast(pd.DataFrame, df[
        (df["End Time"] > analysis_start) &
        (df["Start Time"] < analysis_end)
    ].copy())

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
        hour = run_start.floor("h")     # First hour touched by the run

        while hour < run_end:
            hour_end = hour + pd.Timedelta(hours=1)
            overlap_start = max(run_start, hour)
            overlap_end = min(run_end, hour_end)

            overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
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
    scaffold["Run Minutes"] = scaffold["Run Minutes"].clip(upper=60)    # Limit hour to 60 minutes

    # --------------------------------------------------------
    # Calculate utilisation
    # --------------------------------------------------------

    scaffold["Available Minutes"] = 60
    scaffold["Utilisation"] = (scaffold["Run Minutes"] / scaffold["Available Minutes"])
    scaffold["Date"] = scaffold["Hour Start"].dt.date
    scaffold["Hour"] = scaffold["Hour Start"].dt.hour

    return scaffold[[
        "Instrument",
        "Date",
        "Hour",
        "Hour Start",
        "Run Minutes",
        "Available Minutes",
        "Utilisation",
    ]]

# =========================================================================
# PIPELINE ENTRY POINT (matches the style of _CleanRawLogfiles.run_cleaner,
# _CheckHistoricLogs.check_stale_instruments, etc.)
# =========================================================================

def run_hourly_utilisation(
    summary_file: Path,
    output_file: Path,
    logger,
    *,
    days: int = 100,
    exclude_weekends: bool = True,
    include_idle_instruments: bool = False,
) -> None:

    # Check the summary_file is readable
    try:
        df = pd.read_csv(summary_file)
    except Exception:
        logger.exception(f"Failed to read {summary_file}")
        return

    # Calculate the hourly utilisation
    try:
        result = calc_hourly_util(
            df,
            days,
            include_idle_instruments=include_idle_instruments,
        )
    except Exception:
        logger.exception("Failed to calculate hourly utilisation")
        return

    # Optionally exclude weekend rows before writing out
    if exclude_weekends:
        result = result[pd.to_datetime(result["Date"]).dt.weekday < 5]  # Mon=0 ... Sun=6

    # Drop hours with no recorded run time - only rows with actual usage are written
    # result = result[result["Run Minutes"] > 0]

    if result.empty:
        logger.warning(
            f"No utilisation data produced - all rows had zero run minutes "
            f"in the trailing {days} day(s)."
        )
        return

    # Create output file
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_file, index=False)
        logger.info(
            f"Wrote hourly utilisation for {result['Instrument'].nunique()} "
            f"instrument(s) across {days} day(s) "
            f"({len(result)} rows) to {output_file}"
        )
    except OSError:
        logger.exception(f"Failed to write {output_file}")
        return