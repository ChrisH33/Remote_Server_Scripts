import sys
from pathlib import Path
import argparse
from Logging_Util import get_logger
from Logfile_Analyser.Generic._GenParseLogs import run_parser
from Logfile_Analyser.Generic._TableauIntegrations import publish_csv_to_tableau
from Logfile_Analyser.Generic._CheckHistoricLogs import check_stale_instruments
from Logfile_Analyser.Generic._HourlyUtilisation import run_hourly_utilisation
from SlackClientWrapper.Slack_Connector import SlackClientWrapper
from SlackClientWrapper import _config as slack_config


# =========================================================================
# CONFIG - the settings you're most likely to want to change
# =========================================================================

STEPS_TO_RUN = {
    "parse_logs":           True,   # Condense traces into a single .csv
    "create_log_hyper":     False,   # Convert tidy csv into a hyper file
    "create_util":          False,   # Create a utilisation report
    "create_util_hyper":    False,   # Convert tidy csv into a hyper file
    "check_stale":          False,   # Create a warning if an instrument has gone quiet for too long
    "send_slack":           False,   # Send an update to Slack informing users of run success
}

UTIL_FIELDS = [
    ("instrument",              "Instrument",           "text"),
    ("date",                    "Date",                 "date"),
    ("hour",                    "Hour",                 "int"),
    ("hour_start",              "Hour Start",           "datetime"),
    ("run_minutes",             "Run Minutes",          "float"),
    ("available_minutes",       "Available Minutes",    "int"),
    ("utilisation",             "Utilisation",          "float"),
]

LOG_FIELDS = [
    ("instrument",              "Instrument",           "text"),
    ("filename",                "Filename",             "text"),
    ("start_time",              "Start Time",           "datetime"),
    ("end_time",                "End Time",             "datetime"),
    ("status",                  "Status",               "text"),
    ("sim_mode",                "Sim Mode",             "text"),
    ("method",                  "Method",               "text"),
    ("run_duration_minutes",    "Run Duration (min)",   "float"),
    ("run_date",                "Run Date",             "date"),
    ("process_type",            "Process Type",         "text"),
    ("method_simplified",       "Method Simp.",         "text"),
]

# =========================================================================
# INSTRUMENT REGISTRY
# Everything that differs between instruments lives here. To add a new
# instrument, add an entry — no other code in this file needs to change.
# =========================================================================

# ----- Pick the Folder -----
# PARENT_DIR = Path(r"\\file01-s0\0.051 Research & Development\Instrumentation\Logfiles")  # <-- Logfile location
# PARENT_DIR = Path(r"W:\0.051 Research & Development\Instrumentation\Logfiles")  # <-- Logfile location
PARENT_DIR = Path(r"C:\Users\ch33\Documents")

# ----- Pick an instrument -----
# INSTRUMENT = "Bravo"
INSTRUMENT = "Hamilton"

INSTRUMENT_DIR = PARENT_DIR / INSTRUMENT
logger = get_logger(f"{INSTRUMENT}_logs")

LOGFILES_CSV = INSTRUMENT_DIR / "TidyLogs_ForTableau.csv"
UTILISATION_CSV = INSTRUMENT_DIR / "InstrumentUtilisation.csv"
STALE_INSTRUMENT_TXT = INSTRUMENT_DIR / "stale_instruments.txt"

TABLEAU_PROJECT_ID = "0c88cccd-6f5c-4cd5-9641-f01c10fdbc3e"
LOGFILES_TABLEAU = f"{INSTRUMENT} Tidy Logs"
UTILISATION_TABLEAU = f"{INSTRUMENT} Utilisation"

def step_trace(str, step):
    step = f"Step {STEPS_TO_RUN.index(step) + 1}/{len(STEPS_TO_RUN)}"
    str = str.lower()
    if str == "start":
        logger.info(f"========== {step}: Running step ==========")
    elif str == "error":
        logger.exception(f"!! {step} failed - stopping workflow")
        sys.exit(1)
    elif str == "end":
        logger.info(f"---------- {step}: Skipping step ----------")

# =========================================================================
# MAIN SCRIPT - performs the full workflow for whichever instrument is passed
# =========================================================================


def main(instrument: str) -> None:

    # 1. Condense traces into a single .csv
    # ---------------------------------------------------------------------
    step = "parse_logs"
    if STEPS_TO_RUN[step]:
        step_trace("start", step)
        try:
            if INSTRUMENT_DIR.exists():
                run_parser(
                    log_folder=INSTRUMENT_DIR,
                    output_file=LOGFILES_CSV,
                    fields=LOG_FIELDS,
                    logger=logger
                )
            else:
                raise FileNotFoundError("Instrument log folder not found")
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)



    # 2. Create Utilisation Report
    # ---------------------------------------------------------------------
    step = "create_util"
    if STEPS_TO_RUN[step]:
        step_trace("start", step)
        try:
            if LOGFILES_CSV.exists():
                run_hourly_utilisation(
                    summary_file=LOGFILES_CSV,
                    output_file=UTILISATION_CSV,
                    logger=logger
                )
            else:
                raise FileNotFoundError("Tidy log.csv file not found")
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)



    # 3. Create a hyper file & send to Tableau
    # ---------------------------------------------------------------------
    step = "create_log_hyper"
    if STEPS_TO_RUN[step]:
        step_trace("start", step)
        try:
            if LOGFILES_CSV.exists():
                publish_csv_to_tableau(
                    csv_path=LOGFILES_CSV,
                    datasource_name=LOGFILES_TABLEAU,
                    column_headers=LOG_FIELDS,
                    project_id=TABLEAU_PROJECT_ID,
                    logger=logger
                )
            else:
                raise FileNotFoundError("Tidy log.csv file not found")
        except Exception:
            step_trace("error", step)  
    else:
        step_trace("end", step)



    # 4. Create a hyper file & send to Tableau
    # ---------------------------------------------------------------------
    step = "create_util_hyper"
    if STEPS_TO_RUN[step]:
        step_trace("start", step)
        try:
            if UTILISATION_CSV.exists():
                publish_csv_to_tableau(
                    csv_path=UTILISATION_CSV,
                    datasource_name=UTILISATION_TABLEAU,
                    column_headers=UTIL_FIELDS,
                    project_id=TABLEAU_PROJECT_ID,
                    logger=logger
                )
            else:
                raise FileNotFoundError("Utilisation.csv file not found")
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)



    # 5. Check Instrument Activity
    # ---------------------------------------------------------------------
    step = "check_stale"
    if STEPS_TO_RUN[step]:
        step_trace("start", step)
        try:
            if LOGFILES_CSV.exists():
                check_stale_instruments(
                    log_csv=LOGFILES_CSV,
                    output_txt=STALE_INSTRUMENT_TXT,
                    logger=logger
                )
            else:
                raise FileNotFoundError("Tidy log.csv file not found")
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)



    # 6. Optional Slack notification
    # ---------------------------------------------------------------------
    step = "send_slack"
    if STEPS_TO_RUN[step]:
        step_trace("start", step)
        try:
            slack = SlackClientWrapper(bot_token=slack_config.SLACK_BOT_TOKEN)
            slack.send_message(
                channel=slack_config.PRIVATE_CHANNEL_ID,
                text=getattr("", "SLACK_COMPLETION_MESSAGE", f"{instrument.title()} logs pipeline complete ✅"),
            )
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)


if __name__ == "__main__":
    main()