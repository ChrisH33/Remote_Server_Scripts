import os
import logging
import time
import platform
import shutil
import errno
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# >>>>>>>>>> CONFIG <<<<<<<<<<
windows_prefix = "W:/"
linux_prefix = "/mnt/dna_pipelines/"
network_subdir = "0.253 Short Read (SR)/1. Short Read Library creation/8. MAVE_SGE/SGE Upload"
prod = platform.system() == 'Linux'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')
FOLDER_ID = '1JOOmTIqWHy2xGuJD5t78Z6N6tdydvR3h' # 'CRITICAL - MAVE Data Upload' Folder

# Absolute directories
network_dir = os.path.join(linux_prefix if prod else windows_prefix, network_subdir)
processed_dir = os.path.join(network_dir, "Processed")
os.makedirs(processed_dir, exist_ok=True)

# >>>>>>>>>> LOGGING <<<<<<<<<<
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# >>>>>>>>>> FUNCTIONS <<<<<<<<<<
def script_wait(seconds=10):
    time.sleep(seconds)

def move_to_processed(file_path):
    try:
        dest_path = os.path.join(processed_dir, os.path.basename(file_path))
        shutil.move(file_path, dest_path)
    except Exception as e:
        logger.error(f"Failed to move file {file_path} to processed: {e}")

def upload_file(file_path):
    try:
        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        new_name = base_name

        # Escape single quotes for the Drive query
        escaped_name = base_name.replace("'", "\\'")

        # Check if a file with the same name already exists
        query = f"'{FOLDER_ID}' in parents and name = '{escaped_name}' and trashed = false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])

        counter = 1
        while files:
            new_name = f"{name}_({counter}){ext}"
            escaped_name = new_name.replace("'", "\\'")
            query = f"'{FOLDER_ID}' in parents and name = '{escaped_name}' and trashed = false"
            results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = results.get('files', [])
            counter += 1

        # Upload with final unique name
        file_metadata = {'name': new_name, 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f"Uploaded  {base_name} with File ID: {file.get('id')}")
        return True

    except Exception as e:
        logger.error(f"Failed to upload file {file_path}: {e}")
        return False

def is_file_ready(file_path):
    """Return True if the file is not being written to or locked"""
    try:
        with open(file_path, 'rb'):
            return True
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EBUSY):  # permission denied / resource busy
            return False
        raise
    
# >>>>>>>>>> GOOGLE DRIVE AUTH <<<<<<<<<<
creds = None
# Load cached token
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

# Authenticate if no valid credentials
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    # Save token for future runs
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

# Build the Drive service
service = build('drive', 'v3', credentials=creds)

# >>>>>>>>>> MAIN LOOP <<<<<<<<<<
while True:
    # Check the upload folder is accessible
    if not os.path.isdir(network_dir):
        logger.error(f"Cannot access the network directory: {network_dir}")
        script_wait()
        continue

    # Find CSV files
    try:
        files = [f for f in os.listdir(network_dir) if f.lower().endswith((".csv", ".pdf"))]
        if not files:
            script_wait()
            continue
    except Exception as e:
        logger.error(f"Error accessing files: {e}")
        script_wait()
        continue

    # Upload each file and move to processed if successful
    for file_name in files:
        full_path = os.path.join(network_dir, file_name)

        # Check file readiness
        if not is_file_ready(full_path):
            logger.warning(f"File {file_name} is busy or still being written — skipping this cycle.")
            continue

        if upload_file(full_path):
            time.sleep(2)
            move_to_processed(full_path)

    # Wait a bit before next check (Linux runs continuously, Windows breaks)
    if not prod:
        break

    script_wait()