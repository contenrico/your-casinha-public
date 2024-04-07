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


###--- SEF-RELATED FUNCTIONS ---###

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
    

###--- Invoice-related functions ---###

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES_GMAIL = ['https://www.googleapis.com/auth/gmail.readonly']

def get_message_body(msg):
    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    return None


def get_emails(
        creds_name='credentials.json',
        token_name='gmail_token.pickle',
        emails_name='emails.json'
    ):
    
    # Check if emails.json exists in S3 and was last updated today
    if object_exists(bucket_name, emails_name):
        # Assuming you save the update time in a separate file or use metadata for this
        update_time_object_name = emails_name + "_update_time.txt"
        if object_exists(bucket_name, update_time_object_name):
            update_time_str = download_object(bucket_name, update_time_object_name).decode('utf-8')
            if update_time_str == datetime.today().strftime('%Y-%m-%d'):
                print(f"{emails_name} has already been updated today, {update_time_str}.")
                return f"s3://{bucket_name}/{emails_name}"

    if not object_exists(bucket_name, creds_name):
        raise Exception(f"{creds_name} does not exist in S3 bucket.")

    creds = None

    if object_exists(bucket_name, token_name):
        token_data = download_object(bucket_name, token_name)
        creds = pickle.loads(token_data)

    try:
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds_data = download_object(bucket_name, creds_name)
                flow = InstalledAppFlow.from_client_config(json.loads(creds_data), SCOPES_GMAIL)
                creds = flow.run_local_server(port=0)
            s3.put_object(Bucket=bucket_name, Key=token_name, Body=pickle.dumps(creds))
    except RefreshError:
        creds_data = download_object(bucket_name, creds_name)
        flow = InstalledAppFlow.from_client_config(json.loads(creds_data), SCOPES_GMAIL)
        creds = flow.run_local_server(port=0)
        s3.put_object(Bucket=bucket_name, Key=token_name, Body=pickle.dumps(creds))

    service = build('gmail', 'v1', credentials=creds)
    result = service.users().messages().list(userId='me').execute()
    message_list = []

    for msg in result.get('messages', []):
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        msg_body = get_message_body(msg_data)
        if msg_body:
            payload = msg_data['payload']
            headers = payload['headers']

            subject = next((d['value'] for d in headers if d['name'] == 'Subject'), None)
            sender = next((d['value'] for d in headers if d['name'] == 'From'), None)
            date_str = next((d['value'] for d in headers if d['name'] == 'Date'), None)

            date_match = re.search(r'\d{1,2} \w{3} \d{4} \d{2}:\d{2}:\d{2}', date_str)
            if date_match:
                received_date_str = date_match.group(0)
                received_date = datetime.strptime(received_date_str, '%d %b %Y %H:%M:%S')

                message_dict = {
                    "Subject": subject,
                    "From": sender,
                    "Date": received_date.isoformat(),
                    "Message": msg_body
                }

                message_list.append(message_dict)

    json_buffer = StringIO()
    json.dump(message_list, json_buffer, default=str, indent=2)
    s3.put_object(Bucket=bucket_name, Key=emails_name, Body=json_buffer.getvalue())

    # Update the time this operation was performed
    update_time_str = datetime.today().strftime('%Y-%m-%d')
    s3.put_object(Bucket=bucket_name, Key=update_time_object_name, Body=update_time_str)

    return f"s3://{bucket_name}/{emails_name}"

