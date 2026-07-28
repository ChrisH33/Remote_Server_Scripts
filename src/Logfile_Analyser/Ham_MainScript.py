from src.Logging_Util import get_logger
from src.Logfile_Analyser._CheckHistoricLogs import check_stale_instruments
from src.Logfile_Analyser import Ham_Config as config

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

if __name__ == "__main__":
    main()