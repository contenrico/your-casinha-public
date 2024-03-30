from __future__ import print_function
import os.path
import pandas as pd
from datetime import datetime
import base64
import re
import json
import pickle
import boto3
from io import StringIO

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .aws import *

# Define paths - TODO delete
folder = 'data'
creds_name = 'credentials.json'

### SEF-related API calls ###

# If modifying these scopes, delete the file token.json.
SCOPES_SHEET = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1XNzUH6ydpDt0apgL-a7wuxgxNgRRKMsNwKPpJ74ejbk'
SAMPLE_RANGE_NAME = 'Form Responses 1!A1:AI10000'

    
def get_form(
        creds_name='credentials.json', 
        token_name='sheet_token.json', 
        sheet_name='form_responses.csv'
        ):

    # Check if the credentials file exists in S3
    if not object_exists(bucket_name, creds_name):
        raise Exception(f"{creds_name} does not exist in S3 bucket.")

    # Go through authetication flow
    creds = None

    # The file token.json stores the user's access and refresh tokens and is created 
    # automatically when the authorization flow completes for the first time.
    # Check if the token exists in S3 and load it
    if object_exists(bucket_name, token_name):
        token_data = download_object(bucket_name, token_name)
        creds = Credentials.from_authorized_user_info(json.loads(token_data), SCOPES_SHEET)

    try:
        # Refresh or authenticate credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds_data = download_object(bucket_name, creds_name)
                flow = InstalledAppFlow.from_client_config(json.loads(creds_data), SCOPES_SHEET)
                creds = flow.run_local_server(port=0)
            # Save the credentials back to S3
            s3.put_object(Bucket=bucket_name, Key=token_name, Body=creds.to_json())
    except RefreshError:
        # Handle refresh token errors, re-authenticate, and save new token
        creds_data = download_object(bucket_name, creds_name)
        flow = InstalledAppFlow.from_client_config(json.loads(creds_data), SCOPES_SHEET)
        creds = flow.run_local_server(port=0)
        s3.put_object(Bucket=bucket_name, Key=token_name, Body=creds.to_json())

    # Once authenticated, get the sheet data
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        values = result.get('values', [])

        if not values:
            print('No data found.')
            return

        ### Process the data ###
        # Use the first row as column headers
        columns = values[0]

        # Make column names unique by appending a suffix to duplicates
        unique_columns = []
        seen_columns = {}
        for col in columns:
            if col in seen_columns:
                seen_columns[col] += 1
            else:
                seen_columns[col] = 1

            col = f"{col}_{seen_columns[col]}"    
            unique_columns.append(col)

        data = values[1:]  # Skip the first row (headers)

        # Create a DataFrame with unique column names
        df = pd.DataFrame(data, columns=unique_columns)
        
        # Convert DataFrame to CSV string
        csv_buffer = StringIO()
        df.to_csv(csv_buffer)
        
        # Upload CSV to S3
        s3.put_object(Bucket=bucket_name, Key=sheet_name, Body=csv_buffer.getvalue())

        return f"S3://{bucket_name}/{sheet_name}"

    except HttpError as err:
        print(err)
        return None
    

### Invoice-related API calls ###

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES_GMAIL = ['https://www.googleapis.com/auth/gmail.readonly']

def get_message_body(msg):
    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    return None


def get_emails(
        folder=folder, 
        creds_name=creds_name, 
        token_name='gmail_token.pickle',
        emails_name='emails.json'
        ):
    
    # Check if the folder exists
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Create data paths
    creds_path = os.path.join(folder, creds_name)
    token_path = os.path.join(folder, token_name)
    emails_path = os.path.join(folder, emails_name)

    if os.path.exists(emails_path):
        # Check when emails.json was last updated - if today, return path
        emails_date = pd.to_datetime(os.path.getmtime(emails_path), unit='s').strftime('%d-%m-%Y')

        if emails_date == datetime.today().strftime('%d-%m-%Y'):
            return emails_path

    # Check if the credentials file exists
    if not os.path.exists(creds_path):
        raise Exception(f"{creds_path} does not exist.")

    # Variable creds will store the user access token.
    # If no valid token found, we will create one.
    creds = None

    # The file token.pickle contains the user access token.
    # Check if it exists.
    if os.path.exists(token_path):
        # Read the token from the file and store it in the variable creds.
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If credentials are not available or are invalid, ask the user to log in.
    try:
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES_GMAIL)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

    except RefreshError:
        # If the refresh token is revoked, re-authenticate the user
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES_GMAIL)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    # Connect to the Gmail API.
    service = build('gmail', 'v1', credentials=creds)

    # Request a list of all the messages.
    result = service.users().messages().list(userId='me').execute()

    # Create a list to store messages as dictionaries.
    message_list = []

    # Iterate through all the messages.
    for msg in result.get('messages', []):
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        msg_body = get_message_body(msg_data)
        if msg_body is not None:
            payload = msg_data['payload']
            headers = payload['headers']

            subject = next((d['value'] for d in headers if d['name'] == 'Subject'), None)
            sender = next((d['value'] for d in headers if d['name'] == 'From'), None)
            date_str = next((d['value'] for d in headers if d['name'] == 'Date'), None)

            # Extract the date and time part from the header
            date_match = re.search(r'\d{1,2} \w{3} \d{4} \d{2}:\d{2}:\d{2}', date_str)
            if date_match:
                received_date_str = date_match.group(0)
                received_date = datetime.strptime(received_date_str, '%d %b %Y %H:%M:%S')

                # Create a dictionary for the message.
                message_dict = {
                    "Subject": subject,
                    "From": sender,
                    "Date": received_date.isoformat(),
                    "Message": msg_body
                }

                # Append the message dictionary to the list.
                message_list.append(message_dict)

    with open(emails_path, 'w') as json_file:
        json.dump(message_list, json_file, default=str, indent=2)

    return emails_path