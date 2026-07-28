import sys
from src.Logging_Util import get_logger
from src import credentials as credentials
from src.Logfile_Analyser import Ham_Config as config
from src.Logfile_Analyser._ParseLogs import run_parser
from src.Logfile_Analyser._CleanRawLogfiles import run_cleaner
from src.Logfile_Analyser._CreateHyperFile import create_hyper_from_csv
from src.Logfile_Analyser._PublishHyperToTableau import publish_hyper_to_tableau
from src.Logfile_Analyser._CheckHistoricLogs import check_stale_instruments

# =========================================================================
# STEPS TO RUN - flip any of these to False to skip that step
# =========================================================================

STEPS_TO_RUN = {
    "parse_logs":   True,   # Condense traces into a single .csv
    "clean_logs":   True,   # Tidy raw csv into a Tableau-ready csv
    "create_hyper": True,   # Convert tidy csv into a hyper file
    "publish":      True,   # Push hyper file to Tableau server
    "check_stale":  True,   # Create a warning if an instrument has gone quiet for too long
}

STEP_ORDER = list(STEPS_TO_RUN.keys())

logger = get_logger("Hamilton_parse",config.PYTHON_LOG_FILE)

def step_label(key: str) -> str:
    return f"Step {STEP_ORDER.index(key) + 1}/{len(STEP_ORDER)}"

# =========================================================================
# MAIN SCRIPT - performs the full workflow
# =========================================================================
def main() -> None:

    # 1. Parse Raw Logfiles
    if STEPS_TO_RUN["parse_logs"]:
        logger.info(f"--- {step_label('parse_logs')}: Parsing raw .trc log files ---")
        try:
            run_parser(
                log_folder=config.LOG_FOLDER,
                processed_folder=config.PROCESSED_FOLDER,
                output_file=config.OUTPUT_FILE,
                patterns=config.PATTERNS,
                end_patterns=config.END_PATTERNS,
                abort_patterns=config.ABORT_PATTERNS,
                method_re=config.METHOD_RE,
                serial_re=config.SERIAL_RE,
                fields=config.FIELDS,
                file_ext=config.FILE_EXTENSION,
                max_workers=config.MAX_WORKERS,
                save_batch_size=config.SAVE_BATCH_SIZE,
                save_interval_seconds=config.SAVE_INTERVAL_SECONDS,
                move_files_after_parse=config.MOVE_FILES_AFTER_PARSE,
                logger_name=LOGGER_NAME,
                log_file=config.PARSE_LOG_FILE,
            )
        except Exception:
            logger.exception("Parsing step failed - stopping pipeline")
            sys.exit(1)
    else:
        logger.info(f"--- {step_label('parse_logs')}: Parsing skipped ---")

    # 2. Tidy Raw Logfiles
    if STEPS_TO_RUN["clean_logs"]:
        logger.info(f"--- {step_label('clean_logs')}: Cleaning/tidying results for Tableau ---")
        try:
            run_cleaner(
                state_file=config.STATE_FILE,
                raw_input_file=config.OUTPUT_FILE,
                tidy_output_file=config.TIDY_OUTPUT_FILE,
                tidy_fields=config.TIDY_FIELDS,
                statuses_to_drop=config.STATUSES_TO_DROP,
                filename_prefixes_to_drop=config.FILENAME_PREFIXES_TO_DROP,
                process_types=config.PROCESS_TYPES,
                method_simplified=config.METHOD_SIMPLIFIED,
                pipeline_codes=config.PIPELINE_CODES,
                logger_name=LOGGER_NAME,
                log_file=config.CLEAN_LOG_FILE,
            )
        except Exception:
            logger.exception("Cleaning step failed - stopping pipeline")
            sys.exit(1)
    else:
        logger.info(f"--- {step_label('clean_logs')}: Cleaning skipped ---")

    # 3. Create .hyper from Summarised Logs
    if STEPS_TO_RUN["create_hyper"]:
        logger.info(f"--- {step_label('create_hyper')}: Building Tableau .hyper file ---")
        try:
            create_hyper_from_csv(
                csv_path=config.TIDY_OUTPUT_FILE,
                hyper_path=config.TABLEAU_FILE,
            )
        except Exception:
            logger.exception("Hyper file creation failed - stopping pipeline")
            sys.exit(1)
    else:
        logger.info(f"--- {step_label('create_hyper')}: Hyper file creation skipped ---")

    # 4. Publish .hyper to Tableau Server
    if STEPS_TO_RUN["publish"]:
        logger.info(f"--- {step_label('publish')}: Publishing to Tableau Server ---")
        try:
            publish_hyper_to_tableau(
                config.TABLEAU_FILE,
                config.TABLEAU_PROJECT_ID,
                config.TABLEAU_DATA_NAME,
                server_url=config.TABLEAU_SERVER_ADDRESS,
                site_id=config.TABLEAU_SITE_ID,
                token_name=credentials.TOKEN_NAME,
                token_secret=credentials.TOKEN_SECRET,
            )
        except Exception:
            logger.exception("Publishing step failed - stopping pipeline")
            sys.exit(1)
    else:
        logger.info(f"--- {step_label('publish')}: Publishing skipped ---")

    # 5. Check Instrument Activity
    if STEPS_TO_RUN["check_stale"]:
        logger.info(f"--- {step_label('check_stale')}: Checking instrument activity ---")
        try:
            check_stale_instruments(
                config.TIDY_OUTPUT_FILE,
                config.DAYS_BEFORE_STALE,
                config.LOG_FOLDER,
                config.PROCESSED_FOLDER,
                config.TRACE_FOLDER,
                config.STALE_INSTRUMENTS,
                logger)
        except Exception as e:
            logger.error(f"check_stale_instruments failed: {e}")
    else:
        logger.info(f"--- {step_label('parse')}: Parsing skipped ---")

if __name__ == "__main__":
    main()