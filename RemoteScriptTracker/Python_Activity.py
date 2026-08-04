import time
import os
import platform
import psutil
from RemoteScriptTracker.shared import logger, script_history, active_block_state
from slack_client_wrapper import SlackClientWrapper
from RemoteScriptTracker.status_blocks import update_live_status, rollover_blocks, build_slack_blocks

WRAPPER_KEYWORDS = ['launcher', 'debugpy', 'pythonw.exe']  # ignore these

def get_active_python_scripts() -> set[str]:
    """
    Return a set of Python script filenames currently being executed.

    Scans all running system processes and inspects their command-line arguments.
    Any process whose first argument looks like a Python interpreter and has a
    second (or later) argument pointing to a script file is counted.

    Returns:
        set[str]: A set of script filenames (e.g., {"run_pipeline.py"}).

    Notes:
        - Processes with missing or inaccessible command-line data are skipped.
        - Interpreter-only commands (Python REPL, `python -m`, etc.) are ignored.
        - Only the script's basename is returned.
    """
    scripts = set()

    for proc in psutil.process_iter(['cmdline']):
        cmd = proc.info['cmdline']
        try:
            if not cmd or "python" not in os.path.basename(cmd[0]).lower():
                continue

            for arg in cmd[1:]:
                if any(k in arg.lower() for k in WRAPPER_KEYWORDS):
                    continue
                
                # Only consider actual .py files
                if arg.lower().endswith(".py") and os.path.isfile(arg):
                    scripts.add(os.path.splitext(os.path.basename(arg))[0])
                    break

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return scripts

###################################################################
# --- Get Env Variables ---
CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    logger.critical("Missing SLACK_BOT_TOKEN environment variable")
    raise SystemExit
if not CHANNEL_ID:
    logger.critical("Missing SLACK_CHANNEL_ID environment variable")
    raise SystemExit

# --- Create Slack Wrapper ---
slack_wrapper = SlackClientWrapper(bot_token=SLACK_BOT_TOKEN)

# --- Send Initial Slack Message ---
blocks = build_slack_blocks(script_history, active_block_state)
ts = slack_wrapper.send_message(
    channel=CHANNEL_ID,
    text="Python script status update",
    blocks=blocks
)

###################################################################
# --- Main monitoring loop ---
while True:
    # 1. Detect active scripts
    running_scripts = get_active_python_scripts()

    # 2. Update live 24h block statuses
    update_live_status(running_scripts)

    # 3. Finalize blocks if 24h cycle passed
    rollover_blocks()

    # 4. Build Slack message blocks
    blocks = build_slack_blocks(script_history, active_block_state)

    # 5. Update Slack message
    slack_wrapper.update_message(
        message_ts=ts,
        channel=CHANNEL_ID,
        text="Python script status update",
        blocks=blocks
    )

    # 6. Break loop on non-Linux systems (optional)
    if platform.system() != "Linux":
        break

    # 7. Wait before next check
    time.sleep(300)  # check every 5 minutes