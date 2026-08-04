import sys
from Logging_Util import get_logger
from Logfile_Analyser import credentials as credentials
from Logfile_Analyser import Bravo_Config as config
from Logfile_Analyser.Bravo_ParseLogs import run_parser
from Logfile_Analyser._CleanRawLogfiles import run_cleaner
from Logfile_Analyser._CreateHyperFile import create_hyper_from_csv
from Logfile_Analyser._PublishHyperToTableau import publish_hyper_to_tableau
from Logfile_Analyser._CheckHistoricLogs import check_stale_instruments

workflow = config.STEPS_TO_RUN

STEP_ORDER = list(workflow.keys())

logger = get_logger("Bravo_parse",config.PYTHON_LOG_FILE)

def step_label(key: str) -> str:
    return f"Step {STEP_ORDER.index(key) + 1}/{len(STEP_ORDER)}"

# =========================================================================
# MAIN SCRIPT - performs the full workflow
# =========================================================================
def main() -> None:

    # 1. Parse Raw Logfiles
    # ---------------------------------------------------------------------
    if workflow["parse_logs"]:
        logger.info(f"--- {step_label('parse_logs')}: Parsing raw .trc log files ---")
        try:
            run_parser(
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
            if config.OUTPUT_FILE.exists():
                run_cleaner(
                    raw_input_file=config.OUTPUT_FILE,
                    tidy_output_file=config.TIDY_OUTPUT_FILE,
                    tidy_fields=config.TIDY_FIELDS,
                    statuses_to_drop=config.STATUSES_TO_DROP,
                    filename_prefixes_to_drop=config.FILENAME_PREFIXES_TO_DROP,
                    process_types=config.PROCESS_TYPES,
                    method_simplified=config.METHOD_SIMPLIFIED,
                    pipeline_codes=config.PIPELINE_CODES,
                    logger=logger,
                )
            else:
                raise FileNotFoundError(f"Tidy output file not found: {config.OUTPUT_FILE}")
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
            if config.TIDY_OUTPUT_FILE.exists():
                create_hyper_from_csv(
                    csv_path=config.TIDY_OUTPUT_FILE,
                    hyper_path=config.TABLEAU_FILE,
                    logger=logger,
                )
            else:
                raise FileNotFoundError(f"Tidy output file not found: {config.TIDY_OUTPUT_FILE}")
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
            if config.TABLEAU_FILE.exists():
                publish_hyper_to_tableau(
                    config.TABLEAU_FILE,
                    config.TABLEAU_PROJECT_ID,
                    config.TABLEAU_DATA_NAME,
                    logger,
                    server_url=config.TABLEAU_SERVER_ADDRESS,
                    site_id=config.TABLEAU_SITE_ID,
                    token_name=credentials.TOKEN_NAME,
                    token_secret=credentials.TOKEN_SECRET,
                )
            else:
                raise FileNotFoundError(f"Tidy output file not found: {config.TIDY_OUTPUT_FILE}")
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
            if config.TIDY_OUTPUT_FILE.exists():
                check_stale_instruments(
                    config.TIDY_OUTPUT_FILE,
                    config.DAYS_BEFORE_STALE,
                    config.LOG_FOLDER,
                    config.PROCESSED_FOLDER,
                    config.TRACE_FOLDER,
                    config.STALE_INSTRUMENTS,
                    logger)
            else:
                raise FileNotFoundError(f"Tidy output file not found: {config.TIDY_OUTPUT_FILE}")
        except Exception as e:
            logger.error(f"check_stale_instruments failed: {e}")
    else:
        logger.info(f"--- {step_label('parse')}: Parsing skipped ---")

if __name__ == "__main__":
    main()