import os.path
from typing import Iterable
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def fetch_sheet_data(
    spreadsheet_id: str, spreadsheet_range: str
) -> Iterable[Iterable[str]]:
    """
    Fetches values from google sheet. For creating OAuth credentials see:
    https://developers.google.com/sheets/api/quickstart/python
    Once you have downloaded a json file with your credentials, rename it to
    `google-sheet-credentials.json` and copy it into the root of this repo.
    The first time the script runs it will open a browser window and have you confirm
    that you want this app to use your google account. After confirming it will generate
    a token file with this authorization that it will use in subsequent runs.

    :param spreadsheet_id: id of google sheet, found in url
    :param spreadsheet_range: row/col range to fetch e.g. 'A5:D10'
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("google-sheet-token.json"):
        creds = Credentials.from_authorized_user_file("google-sheet-token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "google-sheet-credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("google-sheet-token.json", "w") as token:
            token.write(creds.to_json())

    service = build("sheets", "v4", credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=spreadsheet_id, range=spreadsheet_range)
        .execute()
    )
    return result.get("values", [])
