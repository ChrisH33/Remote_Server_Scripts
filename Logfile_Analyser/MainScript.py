import sys
import argparse
import importlib
from Logging_Util import get_logger
from creds import Tableau_Credentials as credentials
import Logfile_Analyser.Main_Config as config
from Logfile_Analyser.Generic._CleanRawLogfiles import run_cleaner
from Logfile_Analyser.Generic._CreateHyperFile import create_hyper_from_csv
from Logfile_Analyser.Generic._PublishHyperToTableau import publish_hypers_to_tableau
from Logfile_Analyser.Generic._CheckHistoricLogs import check_stale_instruments, StaleCheckConfig
from Logfile_Analyser.Generic._HourlyUtilisation import run_hourly_utilisation
from SlackClientWrapper.Slack_Connector import SlackClientWrapper
from SlackClientWrapper import _config as slack_config

# =========================================================================
# INSTRUMENT REGISTRY
# Everything that differs between instruments lives here. To add a new
# instrument, add an entry — no other code in this file needs to change.
# =========================================================================

INSTRUMENT_REGISTRY = {
    "bravo": {
        "parser_module": "Logfile_Analyser.Bravo.Bravo_ParseLogs",
        "logger_name": "Bravo_parse",
        "workflow": "BRAVO_STEPS_TO_RUN",
    },
    "hamilton": {
        "parser_module": "Logfile_Analyser.Hamilton.Ham_ParseLogs",
        "logger_name": "Hamilton_Parse",
        "workflow": "HAMILTON_STEPS_TO_RUN",
    },
}

def load_instrument(instrument: str):
    """Import the instrument-specific config + parser and set up its logger."""
    spec = INSTRUMENT_REGISTRY[instrument]
    parser_mod = importlib.import_module(spec["parser_module"])
    logger = get_logger(spec["logger_name"])
    return parser_mod.run_parser, logger

# =========================================================================
# MAIN SCRIPT - performs the full workflow for whichever instrument is passed
# =========================================================================
def main(instrument: str) -> None:
    run_parser, logger = load_instrument(instrument)
    workflow = config.WORKFLOW
    STEP_ORDER = list(workflow.keys())

    # Check the Instrument Config is loaded correctly
    if instrument.lower() not in config.INSTRUMENT_DIR.name.lower():
        logger.info(f"!! Wrong instrument selected in Main_Config.py")
        return

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
    if workflow[step]:
        step_trace("start", step)
        try:
            if config.INSTRUMENT_DIR.exists():
                run_parser(
                    log_folder=config.INSTRUMENT_DIR,
                    processed_folder=config.PROCESSED_DIR,
                    output_file=config.SUMMARY_RAW_CSV,
                    logger=logger
                )
            else:
                raise FileNotFoundError("Instrument log folder not found")
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)

    # 2. Tidy raw csv into a Tableau-ready csv
    # ---------------------------------------------------------------------
    step = "clean_logs"
    if workflow[step]:
        step_trace("start", step)
        try:
            run_cleaner(
                raw_input_file=config.SUMMARY_RAW_CSV,
                tidy_output_file=config.SUMMARY_TIDY_CSV,
                logger=logger,
            )
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)

    # 3. Convert tidy csv into a hyper file
    # ---------------------------------------------------------------------
    step = "create_log_hyper"
    if workflow[step]:
        step_trace("start", step)
        try:
            if config.SUMMARY_TIDY_CSV.exists():
                create_hyper_from_csv(
                    csv_path=config.SUMMARY_TIDY_CSV,
                    hyper_path=config.SUMMARY_TIDY_HYPER,
                    column_headers=config.CSV_FIELDS,
                    logger=logger,
                )
            else:
                raise FileNotFoundError("Tidy log.csv file not found")
        except Exception:
            step_trace("error", step)  
    else:
        step_trace("end", step)

    # 4. Create Utilisation Report
    # ---------------------------------------------------------------------
    step = "create_util"
    if workflow[step]:
        step_trace("start", step)
        try:
            if config.SUMMARY_TIDY_CSV.exists():
                run_hourly_utilisation(
                    summary_file=config.SUMMARY_TIDY_CSV,
                    output_file=config.UTILISATION_CSV,
                    exclude_weekends=config.EXCLUDE_WEEKENDS,
                    days=40,
                    logger=logger,
                )
            else:
                raise FileNotFoundError("Tidy log.csv file not found")
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)

    # 5. Convert utilisation csv into a hyper file
    # ---------------------------------------------------------------------
    step = "create_util_hyper"
    if workflow[step]:
        step_trace("start", step)
        try:
            if config.UTILISATION_CSV.exists():
                create_hyper_from_csv(
                    csv_path=config.UTILISATION_CSV,
                    hyper_path=config.UTILISATION_HYPER,
                    column_headers=config.UTIL_FIELDS,
                    logger=logger,
                )
            else:
                raise FileNotFoundError("Utilisation.csv file not found")
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)

    # 5. Publish .hyper's to Tableau Server
    # ---------------------------------------------------------------------
    step = "publish_hypers"
    if workflow[step]:
        step_trace("start", step)
        try:
            if config.SUMMARY_TIDY_HYPER.exists() or config.UTILISATION_HYPER.exists():
                publish_hypers_to_tableau(
                    datasets=config.TABLEAU_DATASETS,
                    project_id=config.TABLEAU_PROJECT_ID,
                    logger=logger,
                    server_url=config.TABLEAU_SERVER_ADDRESS,
                    site_id=config.TABLEAU_SITE_ID,
                    token_name=credentials.TOKEN_NAME,
                    token_secret=credentials.TOKEN_SECRET,
                )
            else:
                raise FileNotFoundError(f"hyper input file not found")
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)

    # 6. Check Instrument Activity
    # ---------------------------------------------------------------------
    step = "check_stale"
    if workflow[step]:
        step_trace("start", step)
        try:
            if config.SUMMARY_TIDY_CSV.exists():
                check_stale_instruments(
                    StaleCheckConfig(
                        tidy_csv=config.SUMMARY_TIDY_CSV,
                        log_folder=config.INSTRUMENT_DIR,
                        processed_folder=config.PROCESSED_DIR,
                        warning_file=config.STALE_INSTRUMENT_CSV,
                        stale_days=config.DAYS_BEFORE_STALE,
                    ),
                    logger,
                )
            else:
                raise FileNotFoundError("Tidy log.cvs file not found")
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)

    # 7. Optional Slack notification
    # ---------------------------------------------------------------------
    step = "send_slack"
    if workflow[step]:
        step_trace("start", step)
        try:
            slack = SlackClientWrapper(bot_token=slack_config.SLACK_BOT_TOKEN)
            slack.send_message(
                channel=slack_config.PRIVATE_CHANNEL_ID,
                text=getattr(config, "SLACK_COMPLETION_MESSAGE", f"{instrument.title()} logs pipeline complete ✅"),
            )
        except Exception:
            step_trace("error", step)
    else:
        step_trace("end", step)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Run the Logfile Analyser pipeline for a given instrument.")
    arg_parser.add_argument("instrument", choices=sorted(INSTRUMENT_REGISTRY.keys()), help="Which instrument pipeline to run")
    args = arg_parser.parse_args()
    main(args.instrument)