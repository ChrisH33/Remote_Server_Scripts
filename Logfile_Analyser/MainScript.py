import sys
from pathlib import Path
import argparse
from Logging_Util import get_logger
from Logfile_Analyser.Generic._GenParseLogs import run_parser
from Logfile_Analyser.Generic._TableauIntegrations import create_hyper_from_csv
from Logfile_Analyser.Generic._CheckHistoricLogs import check_stale_instruments
from Logfile_Analyser.Generic._HourlyUtilisation import run_hourly_utilisation
from SlackClientWrapper.Slack_Connector import SlackClientWrapper
from SlackClientWrapper import _config as slack_config

# ----- Pick the Folder -----
# PARENT_DIR = Path(r"\\file01-s0\0.051 Research & Development\Instrumentation\Logfiles")  # <-- Logfile location
# PARENT_DIR = Path(r"W:\0.051 Research & Development\Instrumentation\Logfiles")  # <-- Logfile location
PARENT_DIR = Path(r"C:\Users\ch33\Documents")

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

# =========================================================================
# INSTRUMENT REGISTRY
# Everything that differs between instruments lives here. To add a new
# instrument, add an entry — no other code in this file needs to change.
# =========================================================================

def load_instrument(instrument: str):
    """Import the instrument-specific config + parser and set up its logger."""
    INSTRUMENT_DIR = PARENT_DIR / instrument
    logger = get_logger(f"{instrument}_logs")

    LOGFILES_CSV = INSTRUMENT_DIR / "TidyLogs_ForTableau.csv"
    UTILISATION_CSV = INSTRUMENT_DIR / "InstrumentUtilisation.csv"
    STALE_INSTRUMENT_TXT = INSTRUMENT_DIR / "stale_instruments.txt"

    LOGFILES_HYPER = INSTRUMENT_DIR / "TidyLogs.hyper"
    UTILISATION_HYPER = INSTRUMENT_DIR / "InstrumentUtilisation.hyper"

    TABLEAU_DB_LOG_NAME = f"{instrument} Tidy Logs"
    TABLEAU_DB_UTIL_NAME = f"{instrument} Utilisation"
    TABLEAU_DATASETS = [
        (LOGFILES_HYPER, TABLEAU_DB_LOG_NAME),
        (UTILISATION_HYPER, TABLEAU_DB_UTIL_NAME),
    ]

    return INSTRUMENT_DIR, logger, LOGFILES_CSV, UTILISATION_CSV, STALE_INSTRUMENT_TXT, LOGFILES_HYPER, UTILISATION_HYPER, TABLEAU_DATASETS

# =========================================================================
# MAIN SCRIPT - performs the full workflow for whichever instrument is passed
# =========================================================================

def main(instrument: str) -> None:
    INSTRUMENT_DIR, logger, LOGFILES_CSV, UTILISATION_CSV, STALE_INSTRUMENT_TXT, LOGFILES_HYPER, UTILISATION_HYPER, TABLEAU_DATASETS = load_instrument(instrument)
    STEP_ORDER = list(STEPS_TO_RUN.keys())

    def step_trace(str, step):
        step = f"Step {STEP_ORDER.index(step) + 1}/{len(STEP_ORDER)}"
        str = str.lower()
        if str == "start":
            logger.info(f"========== {step}: Running step ==========")
        elif str == "error":
            logger.exception(f"!! {step} failed - stopping workflow")
            sys.exit(1)
        elif str == "end":
            logger.info(f"---------- {step}: Skipping step ----------")

    # 1. Condense traces into a single .csv
    # ---------------------------------------------------------------------
    step = "parse_logs"
    if STEPS_TO_RUN[step]:
        step_trace("start", step)
        try:
            if INSTRUMENT_DIR.exists():
                run_parser(log_folder=INSTRUMENT_DIR, output_file=LOGFILES_CSV, logger=logger)
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
                run_hourly_utilisation(summary_file=LOGFILES_CSV, output_file=UTILISATION_CSV, logger=logger)
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
                create_hyper_from_csv(csv_path=LOGFILES_CSV, hyper_path=LOGFILES_HYPER, logger=logger)
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
                create_hyper_from_csv(csv_path=UTILISATION_CSV, hyper_path=UTILISATION_HYPER, logger=logger)
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
                check_stale_instruments(log_csv=LOGFILES_CSV, output_txt=STALE_INSTRUMENT_TXT, logger=logger)
            else:
                raise FileNotFoundError("Tidy log.cvs file not found")
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
    arg_parser = argparse.ArgumentParser(description="Run the Logfile Analyser pipeline for a given instrument.")
    args = arg_parser.parse_args()
    main(args.instrument)