import logging
from datetime import timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

###################################################################

## Maximum number of blocks to store per scripts
MAX_BLOCKS = 15

# Length of a cycle, in hours
CYCLE_TIME = timedelta(minutes=1)

# History of finalised blocks for each script
script_history = {}

# Active block state for scripts in the current cycle
active_block_state = {}

# Start time of the current cycle_time block for each script
block_start_time = {}
