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

    def step_label(key: str) -> str:
        return f"Step {STEP_ORDER.index(key) + 1}/{len(STEP_ORDER)}"

    # 1. Parse Raw Logfiles (instrument-specific parser)
    # ---------------------------------------------------------------------
    if workflow["parse_logs"]:
        logger.info(f"--- {step_label('parse_logs')}: Parsing raw .trc log files ---")
        try:
            run_parser(
                log_folder=configGen.LOG_FOLDER,
                processed_folder=configGen.PROCESSED_FOLDER,
                ignored_folders={configGen.PROCESSED_FOLDER, configGen.TRACE_FOLDER},
                output_file=configGen.OUTPUT_FILE,
                fields=configGen.FIELDS,
                move_files_after_parse=configGen.MOVE_FILES_AFTER_PARSE,
                max_workers=configGen.MAX_WORKERS,
                logger=logger
            )
        except Exception:
            logger.exception("Parsing step failed - stopping pipeline")
            sys.exit(1)
    else:
        logger.info(f"--- {step_label('parse_logs')}: Parsing skipped ---")

    # 2. Tidy Raw Logfiles
    # ---------------------------------------------------------------------
    if workflow["clean_logs"]:
        logger.info(f"--- {step_label('clean_logs')}: Cleaning/tidying results for Tableau ---")
        try:
            if configGen.OUTPUT_FILE.exists():
                run_cleaner(
                    raw_input_file=configGen.OUTPUT_FILE,
                    tidy_output_file=configGen.TIDY_OUTPUT_FILE,
                    tidy_fields=configGen.TIDY_FIELDS,
                    statuses_to_drop=configDev.STATUSES_TO_DROP,
                    filename_prefixes_to_drop=configDev.FILENAME_PREFIXES_TO_DROP,
                    process_types=configDev.PROCESS_TYPES,
                    logger=logger,
                )
            else:
                raise FileNotFoundError(f"Tidy output file not found: {configGen.OUTPUT_FILE}")
        except Exception:
            logger.exception("Cleaning step failed - stopping pipeline")
            sys.exit(1)
    else:
        logger.info(f"--- {step_label('clean_logs')}: Cleaning skipped ---")

    # 3. Create .hyper from Summarised Logs
    # ---------------------------------------------------------------------
    if workflow["create_hyper"]:
        logger.info(f"--- {step_label('create_hyper')}: Building Tableau .hyper file ---")
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
            logger.exception("Hyper file creation failed - stopping pipeline")
            sys.exit(1)
    else:
        logger.info(f"--- {step_label('create_hyper')}: Hyper file creation skipped ---")

    # 4. Publish .hyper to Tableau Server
    # ---------------------------------------------------------------------
    if workflow["publish"]:
        logger.info(f"--- {step_label('publish')}: Publishing to Tableau Server ---")
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
            logger.exception("Publishing step failed - stopping pipeline")
            sys.exit(1)
    else:
        logger.info(f"--- {step_label('publish')}: Publishing skipped ---")

    # 5. Check Instrument Activity
    # ---------------------------------------------------------------------
    if workflow["check_stale"]:
        logger.info(f"--- {step_label('check_stale')}: Checking instrument activity ---")
        try:
            if configGen.TIDY_OUTPUT_FILE.exists():
                check_stale_instruments(
                    configGen.TIDY_OUTPUT_FILE,
                    configGen.DAYS_BEFORE_STALE,
                    configGen.LOG_FOLDER,
                    configGen.PROCESSED_FOLDER,
                    configGen.TRACE_FOLDER,
                    configGen.STALE_INSTRUMENTS,
                    logger)
            else:
                raise FileNotFoundError(f"Tidy output file not found: {configGen.TIDY_OUTPUT_FILE}")
        except Exception as e:
            logger.error(f"check_stale_instruments failed: {e}")
    else:
        logger.info(f"--- {step_label('check_stale')}: Check stale skipped ---")

    # 6. Optional Slack notification
    # ---------------------------------------------------------------------
    if workflow["send_slack"]:
        logger.info(f"--- {step_label('send_slack')}: Sending notification to Slack ---")
        try:
            slack = SlackClientWrapper(bot_token=slack_config.SLACK_BOT_TOKEN)
            slack.send_message(
                channel=slack_config.PRIVATE_CHANNEL_ID,
                text=getattr(configGen, "SLACK_COMPLETION_MESSAGE", f"{instrument.title()} logs pipeline complete ✅"),
            )
        except Exception as e:
            logger.error(f"Send_Slack_Update failed: {e}")
    else:
        logger.info(f"--- {step_label('send_slack')}: Check stale skipped ---")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Run the Logfile Analyser pipeline for a given instrument.")
    arg_parser.add_argument("instrument", choices=sorted(INSTRUMENT_REGISTRY.keys()), help="Which instrument pipeline to run")
    args = arg_parser.parse_args()
    main(args.instrument)