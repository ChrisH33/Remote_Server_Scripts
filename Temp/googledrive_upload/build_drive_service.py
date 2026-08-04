import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def build_drive_service(config):
    """
    Authenticate with Google Drive using stored credentials, refreshing or
    re-running the OAuth flow as needed.

    Returns a Drive API service object.
    """
    creds = None

    # Load cached credentials if they exist
    if os.path.exists(config.google_token):
        creds = Credentials.from_authorized_user_file(config.google_token, config.scopes)

    # Refresh or re-authenticate if credentials are missing or expired
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow  = InstalledAppFlow.from_client_secrets_file(config.credentials, config.scopes)
            creds = flow.run_local_server(port=0)

        # Persist the (possibly refreshed) token so we don't re-auth every run
        with open(config.google_token, "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)