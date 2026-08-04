"""
build_sheets_service.py
-----------------------
Authenticate with Google Sheets using stored credentials, refreshing or
re-running the OAuth flow as needed.
 
Returns a Sheets API service object.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def build_sheets_service(google_token, scopes, credentials):
    """
    Authenticate with Google Sheets using stored credentials, refreshing or
    re-running the OAuth flow as needed.
 
    Returns a Sheets API service object.
    """
    creds = None
    
    # Load cached credentials if they exist
    if os.path.exists(google_token):
        creds = Credentials.from_authorized_user_file(google_token, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials, scopes)
            creds = flow.run_local_server(port=0) 

        # Persist the (possibly refreshed) token so we don't re-auth every run
        with open(google_token, "w") as token:
            token.write(creds.to_json())
  
    return build("sheets", "v4", credentials=creds)