# stdlib
import os
import sys
import time
import platform
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# third-party
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# internal
from config import load_var, logger
from file_mover import move_to_processed, upload_file_to_google

# Shared Ubuntu scripts
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))
import UniFunction
from SlackClientWrapper.slack_client_wrapper.slack_wrapper import SlackClientWrapper


# =================================================================
# Functions
# =================================================================

def build_drive_service(config, scopes):
    creds = None

    if os.path.exists(config.google_token):
        creds = Credentials.from_authorized_user_file(
            config.google_token, scopes
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.credentials, scopes
            )
            creds = flow.run_local_server(port=0)

        with open(config.google_token, "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)

def retry(func, retries: int = 3, delay: float = 1.0, *args, **kwargs):
    """
    Retry a function up to `retries` times, waiting `delay` seconds between attempts.
    Returns the function result if successful, otherwise returns False.
    """
    for attempt in range(1, retries + 1):
        try:
            result = func(*args, **kwargs)
            if result:
                return True
            else:
                logger.warning(f"Attempt {attempt} failed for {func.__name__}: returned False")
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}")
        time.sleep(delay)
    return False

# =================================================================
# Set Config & Slack
# =================================================================

config = load_var()
slack_wrapper = SlackClientWrapper(bot_token=config.slack_bot_token)
service = build_drive_service(config, config.scopes)

# =================================================================
# Main monitoring loop
# =================================================================

while True:
        
    time.sleep(config.refresh_rate)

    try:
        files = [
            f for f in os.listdir(config.network_dir)
            if f.lower().endswith((".csv", ".pdf"))
        ]
    except Exception:
        logger.exception("Error accessing network directory")
        time.sleep(5)
        continue
    if not files:
        time.sleep(config.refresh_rate)
        continue

    uploaded_files: List[str] = []

    for file_name in files:
        full_path = os.path.join(config.network_dir, file_name)

        # Retry upload
        if retry(upload_file_to_google, retries=3, delay=2, file_path=full_path, FOLDER_ID=config.mave_folder_id, service=service):
            # Retry move
            if retry(move_to_processed, retries=3, delay=1, file_path=full_path, dir=config.processed_network_dir):
                uploaded_files.append(file_name)
            else:
                logger.error(f"Failed to move file to processed folder after retries: {full_path}")
        else:
            logger.error(f"Failed to upload file to Google Drive after retries: {full_path}")

    if uploaded_files:
        message_text = f"Uploaded {len(uploaded_files)} file(s) to Google Drive:\n" + "\n".join(uploaded_files)
        slack_wrapper.send_message(
            channel=config.channel_id,
            text=message_text,
            blocks=None,
        )

    # Exit loop if running on Linux (optional)
    if not UniFunction.prod_mode():
        break