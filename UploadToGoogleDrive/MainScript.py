import os
import time
import signal
from typing import List
from UploadToGoogleDrive import _config as config
from UploadToGoogleDrive import CreateGoogleService
from SlackClientWrapper import  as 
from SlackClientWrapper import _config as slack_config
from Logging_Util import get_logger

logger = get_logger("UploadToDrive")

slack  = SlackClientWrapper(bot_token=config.slack_bot_token)
service = CreateGoogleService.build_drive_service(config)

_shutdown_requested = False


def _request_shutdown(signum, frame):
    global _shutdown_requested
    logger.info(f"Received signal {signum} — shutting down after current cycle.")
    _shutdown_requested = True

signal.signal(signal.SIGTERM, _request_shutdown)
signal.signal(signal.SIGINT,  _request_shutdown)


def retry(func, *args, retries: int = 3, delay: float = 1.0, **kwargs):
    for attempt in range(1, retries + 1):
        try:
            result = func(*args, **kwargs)
            if result:
                return result
            logger.warning(
                f"Attempt {attempt}/{retries} failed for {func.__name__}: returned falsy"
            )
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{retries} failed for {func.__name__}: {e}")
        if attempt < retries:
            time.sleep(delay)

    logger.error(f"{func.__name__} failed after {retries} attempts")
    return False




try:
    while not _shutdown_requested:
        # ── Scan network directory for uploadable files
        try:
            files = [
                f for f in os.listdir(config.NETWORK_DIR)
                if f.lower().endswith(config.FILES_TO_UPLOAD)
            ]
        except Exception:
            logger.exception(f"Error Accessing network directory: {config.NETWORK_DIR}")
            time.sleep(config.REFRESH_RATE)
            continue

        # ── Process each file 
        uploaded_files: List[str] = []
        for file_name in files:
            full_path = os.path.join(config.NETWORK_DIR, file_name)

            # 1. Upload File
            if retry(
                upload_to_drive,
                full_path,
                config.MAVE_FOLDER_ID,
                service,
                retries=3,
                delay=2
            ):
                # 2. Relocate File
                if retry(
                    move_to_processed,
                    full_path,
                    config.PROCESSED_DIR
                    retries=3,
                    delay=2
                ):
                    uploaded_files.append(file_name)
                else:
                    logger.error(f"Upload succeeded but move to Processed failed: {full_path}")
            else:
                logger.error(f"Failed to upload to Google Drive after retries: {full_path}")
                  
        # ── Slack summary ─────────────────────────────────────────────────
        if uploaded_files:
            slack.send_message(
                channel=slack_config.PRIVATE_CHANNEL_ID,
                text=(
                    f"Uploaded {len(uploaded_files)} file(s) to Google Drive:\n"
                    + "\n".join(uploaded_files)
                ),
            )

        # ── Break after one cycle on dev machines ─────────────────────────
        if not prod_mode():
            logger.info("Non-Linux environment — exiting after one cycle (dev mode).")
            break

        time.sleep(config.REFRESH_RATE)

except Exception:
    logger.exception("Unexpected error in upload loop")

finally:
    # Always notify Slack on exit so the team knows uploads have stopped
    slack.send_message(channel=Config.channel_id, text=Config.shutdown_message)
    logger.info("Shutdown notice sent to Slack.")