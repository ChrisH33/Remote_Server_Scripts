import sys
import argparse
import importlib
from Logging_Util import get_logger
from creds import Tableau_Credentials as credentials
import Logfile_Analyser.Main_Config as configGen
from Logfile_Analyser.Generic._CleanRawLogfiles import run_cleaner
from Logfile_Analyser.Generic._CreateHyperFile import create_hyper_from_csv
from Logfile_Analyser.Generic._PublishHyperToTableau import publish_hyper_to_tableau
from Logfile_Analyser.Generic._CheckHistoricLogs import check_stale_instruments
from SlackClientWrapper.Slack_Connector import SlackClientWrapper
from SlackClientWrapper import _config as slack_config


"""
- update create hyper to work with multiple csvs
- update send hyper to work with multiple hypers
- update utilisation to function
- update tableau with the new data
"""

# =========================================================================
# INSTRUMENT REGISTRY
# Everything that differs between instruments lives here. To add a new
# instrument, add an entry — no other code in this file needs to change.
# =========================================================================

INSTRUMENT_REGISTRY = {
    "bravo": {
        "config_module": "Logfile_Analyser.Bravo.Bravo_Config",
        "parser_module": "Logfile_Analyser.Bravo.Bravo_ParseLogs",
        "logger_name": "Bravo_parse",
    },
    "hamilton": {
        "config_module": "Logfile_Analyser.Hamilton.Ham_Config",
        "parser_module": "Logfile_Analyser.Hamilton.Ham_ParseLogs",
        "logger_name": "Hamilton_Parse",
    },
}

def load_instrument(instrument: str):
    """Import the instrument-specific config + parser and set up its logger."""
    spec = INSTRUMENT_REGISTRY[instrument]
    config = importlib.import_module(spec["config_module"])
    parser_mod = importlib.import_module(spec["parser_module"])
    logger = get_logger(spec["logger_name"])
    return config, parser_mod.run_parser, logger

# =========================================================================
# MAIN SCRIPT - performs the full workflow for whichever instrument is passed
# =========================================================================
def main(instrument: str) -> None:
    configDev, run_parser, logger = load_instrument(instrument)
    workflow = configDev.STEPS_TO_RUN
    STEP_ORDER = list(workflow.keys())

    # Check the Instrument Config is loaded correctly
    if instrument.lower() not in configGen.LOG_FOLDER.name.lower():
        logger.info(f"!! Wrong instrument selected in Main_Config.py")
        return

    def step_label(key: str) -> str:
        return f"Step {STEP_ORDER.index(key) + 1}/{len(STEP_ORDER)}"

    def step_error(step):
        logger.exception(f"!! {step_label(step)} failed - stopping workflow")
        sys.exit(1)

    # 1. Parse Raw Logfiles (instrument-specific parser)
    # ---------------------------------------------------------------------
    step = "parse_logs"
    if workflow[step]:
        logger.info(f"--- {step_label(step)}: Running step ---")
        try:
            run_parser(
                log_folder=configGen.LOG_FOLDER,
                processed_folder=configGen.PROCESSED_FOLDER,
                ignored_folders={configGen.PROCESSED_FOLDER},
                output_file=configGen.OUTPUT_FILE,
                fields=configGen.FIELDS,
                move_files_after_parse=configGen.MOVE_FILES_AFTER_PARSE,
                max_workers=configGen.MAX_WORKERS,
                logger=logger
            )
        except Exception:
            step_error(step)
    else:
        logger.info(f"--- {step_label(step)}: Step skipped ---")

    # 2. Tidy Raw Logfiles
    # ---------------------------------------------------------------------
    step = "clean_logs"
    if workflow[step]:
        logger.info(f"--- {step_label(step)}: Running step ---")
        try:
            if configGen.OUTPUT_FILE.exists():
                run_cleaner(
                    raw_input_file=configGen.OUTPUT_FILE,
                    tidy_output_file=configGen.TIDY_OUTPUT_FILE,
                    tidy_fields=configGen.TIDY_FIELDS,
                    statuses_to_drop=configDev.STATUSES_TO_DROP,
                    filename_prefixes_to_drop=configDev.FILENAME_PREFIXES_TO_DROP,
                    process_types=configGen.PROCESS_TYPES,
                    logger=logger,
                )
            else:
                raise FileNotFoundError(f"Tidy output file not found: {configGen.OUTPUT_FILE}")
        except Exception:
            step_error(step)
    else:
        logger.info(f"--- {step_label(step)}: Step skipped ---")

    # 3. Create Utilisation Report
    # ---------------------------------------------------------------------
    step = "create_util"
    if workflow[step]:
        logger.info(f"--- {step_label(step)}: Running step ---")
        try:
            if configGen.TIDY_OUTPUT_FILE.exists():
                ...
            else:
                raise FileNotFoundError(f"Tidy output file not found: {configGen.TIDY_OUTPUT_FILE}")
        except Exception:
            step_error(step)
    else:
        logger.info(f"--- {step_label(step)}: Step skipped ---")

    # 4. Create .hyper files
    # ---------------------------------------------------------------------
    step = "create_hyper_files"
    if workflow[step]:
        logger.info(f"--- {step_label(step)}: Running step ---")
        try:
            if configGen.TIDY_OUTPUT_FILE.exists():
                create_hyper_from_csv(
                    csv_path=configGen.TIDY_OUTPUT_FILE,
                    hyper_path=configGen.TABLEAU_FILE,
                    logger=logger,
                )
            else:
                raise FileNotFoundError(f"Tidy output file not found: {configGen.TIDY_OUTPUT_FILE}")
        except Exception:
            step_error(step)
    else:
        logger.info(f"--- {step_label(step)}: Step skipped ---")

    # 5. Publish .hyper's to Tableau Server
    # ---------------------------------------------------------------------
    step = "publish_hypers"
    if workflow[step]:
        logger.info(f"--- {step_label(step)}: Running step ---")
        try:
            if configGen.TABLEAU_FILE.exists():
                publish_hyper_to_tableau(
                    configGen.TABLEAU_FILE,
                    configGen.TABLEAU_PROJECT_ID,
                    configGen.TABLEAU_DATA_NAME,
                    logger,
                    server_url=configGen.TABLEAU_SERVER_ADDRESS,
                    site_id=configGen.TABLEAU_SITE_ID,
                    token_name=credentials.TOKEN_NAME,
                    token_secret=credentials.TOKEN_SECRET,
                )
            else:
                raise FileNotFoundError(f"Tidy output file not found: {configGen.TIDY_OUTPUT_FILE}")
        except Exception:
            step_error(step)
    else:
        logger.info(f"--- {step_label(step)}: Step skipped ---")

    # 6. Check Instrument Activity
    # ---------------------------------------------------------------------
    step = "check_stale"
    if workflow[step]:
        logger.info(f"--- {step_label(step)}: Running step ---")
        try:
            if configGen.TIDY_OUTPUT_FILE.exists():
                check_stale_instruments(
                    configGen.TIDY_OUTPUT_FILE,
                    configGen.DAYS_BEFORE_STALE,
                    configGen.LOG_FOLDER,
                    configGen.PROCESSED_FOLDER,
                    configGen.STALE_INSTRUMENTS,
                    logger)
            else:
                raise FileNotFoundError(f"Tidy output file not found: {configGen.TIDY_OUTPUT_FILE}")
        except Exception:
            step_error(step)
    else:
        logger.info(f"--- {step_label(step)}: Step skipped ---")

    # 7. Optional Slack notification
    # ---------------------------------------------------------------------
    step = "send_slack"
    if workflow["step"]:
        logger.info(f"--- {step_label(step)}: Running step ---")
        try:
            slack = SlackClientWrapper(bot_token=slack_config.SLACK_BOT_TOKEN)
            slack.send_message(
                channel=slack_config.PRIVATE_CHANNEL_ID,
                text=getattr(configGen, "SLACK_COMPLETION_MESSAGE", f"{instrument.title()} logs pipeline complete ✅"),
            )
        except Exception:
            step_error(step)
    else:
        logger.info(f"--- {step_label(step)}: Step skipped ---")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Run the Logfile Analyser pipeline for a given instrument.")
    arg_parser.add_argument("instrument", choices=sorted(INSTRUMENT_REGISTRY.keys()), help="Which instrument pipeline to run")
    args = arg_parser.parse_args()
    main(args.instrument)