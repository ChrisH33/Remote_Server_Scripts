import os
import shutil
import errno
from config import logger
from googleapiclient.http import MediaFileUpload

def move_to_processed(file_path, dir):
    if not is_file_ready(file_path):
        return False
    try:
        file_name = os.path.basename(file_path)
        dest_path = os.path.join(dir, os.path.join(file_name))
        shutil.move(file_path, dest_path)
        return True
    except Exception as e:
        logger.error(f"Failed to move file {file_path} to processed: {e}")
        return False
    
def upload_file_to_google(file_path, FOLDER_ID, service):
    if not is_file_ready(file_path):
        return False
    
    try:
        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        new_name = base_name
        escaped_name = base_name.replace("'","\\")

        # Check if file already exists in Google
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
    try:
        with open(file_path, 'rb'):
            return True
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EBUSY):
            return False
        raise