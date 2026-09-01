import sys
import time
from pathlib import Path
from Logging_Util import get_logger
from Logfile_Analyser.Generic._GenParseLogs import run_parser
from Logfile_Analyser.Generic._TableauIntegrations import publish_csv_to_tableau
from Logfile_Analyser.Generic._CheckHistoricLogs import check_stale_instruments
from Logfile_Analyser.Generic._HourlyUtilisation import run_hourly_utilisation
from SlackClientWrapper.Slack_Connector import SlackClientWrapper
from SlackClientWrapper import _config as slack_config

# =========================================================================
# CONFIG
# =========================================================================

STEPS_TO_RUN = {
    "parse_logs": True,
    "create_log_hyper": True,
    "create_util": True,
    "create_util_hyper": True,
    "check_stale": True,
    "send_slack": True,
}

UTIL_FIELDS = [
    ("instrument", "Instrument", "text"),
    ("date", "Date", "date"),
    ("hour", "Hour", "int"),
    ("hour_start", "Hour Start", "datetime"),
    ("run_minutes", "Run Minutes", "float"),
    ("available_minutes", "Available Minutes", "int"),
    ("utilisation", "Utilisation", "float"),
]

LOG_FIELDS = [
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

# =========================================================================
# ENVIRONMENT
# =========================================================================

PARENT_DIR = Path(r"C:\Users\ch33\Documents")
INSTRUMENT = "Hamilton"
# INSTRUMENT = "Bravo"

INSTRUMENT_DIR = PARENT_DIR / INSTRUMENT
logger = get_logger(f"{INSTRUMENT}_logs")

LOGFILES_CSV = INSTRUMENT_DIR / "TidyLogs_ForTableau.csv"
UTILISATION_CSV = INSTRUMENT_DIR / "InstrumentUtilisation.csv"
STALE_INSTRUMENT_TXT = INSTRUMENT_DIR / "stale_instruments.txt"

TABLEAU_PROJECT_ID = "0c88cccd-6f5c-4cd5-9641-f01c10fdbc3e"
LOGFILES_TABLEAU = f"{INSTRUMENT} Tidy Logs"
UTILISATION_TABLEAU = f"{INSTRUMENT} Utilisation"


# =========================================================================
# LOGGING
# =========================================================================

def step_trace(status, step_label):
    status = status.lower()
    if status == "start":
        logger.info(f"========== {step_label}: Running step ==========")
    elif status == "error":
        logger.exception(f"!! {step_label} failed - stopping workflow")
        sys.exit(1)
    elif status == "end":
        logger.info(f"---------- {step_label}: Skipping step ----------")

# =========================================================================
# STEP FUNCTIONS
# =========================================================================

def run_parse_logs():
    if not INSTRUMENT_DIR.exists():
        raise FileNotFoundError("Instrument log folder not found")
    run_parser(
        log_folder=INSTRUMENT_DIR,
        output_file=LOGFILES_CSV,
        fields=LOG_FIELDS,
        logger=logger,
        move_files=False
    )

def run_create_util():
    if not LOGFILES_CSV.exists():
        raise FileNotFoundError("Tidy log.csv file not found")
    run_hourly_utilisation(
        summary_file=LOGFILES_CSV,
        output_file=UTILISATION_CSV,
        logger=logger
    )

def run_create_log_hyper():
    if not LOGFILES_CSV.exists():
        raise FileNotFoundError("Tidy log.csv file not found")
    publish_csv_to_tableau(
        csv_path=LOGFILES_CSV,
        datasource_name=LOGFILES_TABLEAU,
        column_headers=LOG_FIELDS,
        project_id=TABLEAU_PROJECT_ID,
        logger=logger
    )

def run_create_util_hyper():
    if not UTILISATION_CSV.exists():
        raise FileNotFoundError("Utilisation.csv file not found")
    publish_csv_to_tableau(
        csv_path=UTILISATION_CSV,
        datasource_name=UTILISATION_TABLEAU,
        column_headers=UTIL_FIELDS,
        project_id=TABLEAU_PROJECT_ID,
        logger=logger
    )

def run_check_stale():
    if not LOGFILES_CSV.exists():
        raise FileNotFoundError("Tidy log.csv file not found")
    check_stale_instruments(
        log_csv=LOGFILES_CSV,
        output_txt=STALE_INSTRUMENT_TXT,
        logger=logger
    )

def run_send_slack():
    slack = SlackClientWrapper(bot_token=slack_config.SLACK_BOT_TOKEN)
    message = getattr(
        slack_config,
        "SLACK_COMPLETION_MESSAGE",
        f"{INSTRUMENT.title()} logs pipeline complete ✅"
    )
    slack.send_message(
        channel=slack_config.PRIVATE_CHANNEL_ID,
        text=message,
    )

# =========================================================================
# PIPELINE DEFINITION (single source of truth)
# =========================================================================

PIPELINE = [
    ("parse_logs", run_parse_logs),
    ("create_util", run_create_util),
    ("create_log_hyper", run_create_log_hyper),
    ("create_util_hyper", run_create_util_hyper),
    ("check_stale", run_check_stale),
    ("send_slack", run_send_slack),
]

# =========================================================================
# MAIN
# =========================================================================

def main():
    total_steps = len(PIPELINE)

    for i, (step_name, func) in enumerate(PIPELINE, start=1):
        step_label = f"Step {i}/{total_steps}"

        if not STEPS_TO_RUN.get(step_name, False):
            step_trace("end", step_label)
            continue

        step_trace("start", step_label)

        try:
            func()
        except Exception:
            step_trace("error", step_label)


if __name__ == "__main__":
    start = time.time()
    main()
    elapsed = time.time() - start
    mins, secs = divmod(elapsed, 60)
    logger.info(f"Total runtime: {int(mins)}m {secs:.1f}s")