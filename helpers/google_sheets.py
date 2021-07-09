import os.path
import json
from typing import Iterable
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from rich.console import Console

console = Console()


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
NFT_SHEET_ID = "1tLRI7Bk7d4d1mCYGxoI6uIFvj1eA8-9jhCXvgXxWiDA"


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


def address_data_to_json(data: Iterable[Iterable[str]], columns: Iterable[str]):
    """
    converts table of user data to json

    :param data: 2d array of data
    :param columns: array of labels for each column, length should be 1 less than 
                    length of inner array of data since first first item becomes 
                    the key for that entry.
    """
    res = {}
    if len(data) < 1:
        raise ValueError("No data")

    for row in data:
        res[row[0]] = {}
        for idx, col in enumerate(columns):
            if idx + 1 < len(row):
                if col:
                    res[row[0]][col] = row[idx + 1]

    return res


def build_dict(
    data: Iterable[Iterable[str]], name: str, key_idx: int, data_idx: int
) -> dict:
    """
    build a dictionary from sheet data

    :param data: 2D array of spreadsheet data
    :param name: select every row from data that has name in its first column
    :param key_idx: each entry in the dictionary will have the value at this column index as its key
    :param data_idx: each entry in the dictionary will have the value at this row index as its value
    """
    print(data)
    filtered_data = [row for row in data if (len(row) > 0 and name in row[0])]
    dict = {}
    for row in filtered_data:
        dict[row[key_idx]] = row[data_idx]
    return dict


def nft_metadata(spreadsheet_id: str, spreadsheet_range: str):
    """
    build the data structures to be processed

    :param spreadsheet_id: id of google sheet, found in url
    :param spreadsheet_range: row/col range to fetch e.g. 'A5:D10'
    """
    sheet_data = fetch_sheet_data(spreadsheet_id, spreadsheet_range)
    honeypot_rarity = build_dict(sheet_data, "Honeypot", 4, 1)
    diamond_hands_rarity = build_dict(sheet_data, "Diamond Hands", 4, 1)
    jersey_rarity = build_dict(sheet_data, "Jersey", 4, 1)
    memeAddress = next(filter(lambda row: "Honeypot" in row[0], sheet_data), None)[2]
    badgerNftAddress = next(filter(lambda row: "Jersey" in row[0], sheet_data), None)[2]
    return (
        honeypot_rarity,
        diamond_hands_rarity,
        jersey_rarity,
        memeAddress,
        badgerNftAddress,
    )


def fetch_all_nft_data():
    """
    fetch all nft data and dump to a json file
    """
    (
        honeypot_rarity,
        diamond_hands_rarity,
        jersey_rarity,
        memeAddress,
        badgerNftAddress,
    ) = nft_metadata(NFT_SHEET_ID, "A5:J14")

    max_nft_boost = (
        float(fetch_sheet_data(NFT_SHEET_ID, "H2:I2")[0][1].strip("%")) / 100
    )
    score_multipliers = build_dict(fetch_sheet_data(NFT_SHEET_ID, "D1:F3"), "", 0, 2)

    nft_data = {
        "MAX_NFT_BOOST": max_nft_boost,
        "score_multipliers": score_multipliers,
        "honeypot_rarity": honeypot_rarity,
        "diamond_hands_rarity": diamond_hands_rarity,
        "jersey_rarity": jersey_rarity,
        "memeAddress": memeAddress,
        "badgerNftAddress": badgerNftAddress,
    }

    with open("nft_data.json", "w") as outfile:
        json.dump(nft_data, outfile, indent=4)


def fetch_all_user_data():
    """
    fetch all user data and dump to json file
    """
    address_data = fetch_sheet_data(NFT_SHEET_ID, "A19:M831")
    columns = fetch_sheet_data(NFT_SHEET_ID, "B17:M17")[0]
    user_data = address_data_to_json(address_data, columns)

    with open("user_data.json", "w") as outfile:
        json.dump(user_data, outfile, indent=4)


def get_json_data(name: str):
    file_name = name + "_data.json"
    if not os.path.exists(file_name):
        raise ValueError(
            file_name
            + " not found. Run the script in helpers/google_sheets.py to generate"
        )

    with open(file_name) as json_file:
        return json.load(json_file)


# fetch_all_user_data()
# fetch_all_nft_data()
