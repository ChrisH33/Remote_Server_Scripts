import sys
from src.Logging_Util import get_logger
from _CheckHistoricLogs import check_stale_instruments
import Ham_Config as config

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
                30,
                config.LOG_FOLDER,
                config.PROCESSED_FOLDER,
                config.PYTHON_LOG_FILE,
                logger)
        except:
            print("")