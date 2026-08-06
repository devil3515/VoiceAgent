from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds = Credentials.from_authorized_user_file(
        "token.json",
        SCOPES
    )

    return build("calendar", "v3", credentials=creds)