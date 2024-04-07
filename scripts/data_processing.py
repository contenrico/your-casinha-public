import os
import json
import pandas as pd
import re
from datetime import datetime

from .aws import *


### SEF processing functions ###

def clean_sheet(sheet_name='form_responses.csv'):

    # Read the original CSV file into a DataFrame
    obj = s3.get_object(Bucket=bucket_name, Key=sheet_name)
    df = pd.read_csv(obj['Body']).drop(columns=['Unnamed: 0'])

    # Melt the DataFrame to reshape it
    melted_df = pd.melt(df, id_vars=['Timestamp_1'], var_name='Variable', value_name='Value')

    # Extract the part after the underscore to get the column name and number
    melted_df['Column_Name'] = melted_df['Variable'].str.split('_').str[0]
    melted_df['Column_No'] = melted_df['Variable'].str.split('_').str[-1]

    # Remove unnecessary data
    melted_df = melted_df[melted_df['Column_Name'] != 'Number of guests']
    melted_df = melted_df.drop(columns=['Variable'])

    # Pivot the DataFrame and clean it
    pivoted_df = melted_df.pivot(index=['Timestamp_1', 'Column_No'], columns='Column_Name', values='Value').reset_index()
    pivoted_df.columns.name = None
    pivoted_df = pivoted_df.dropna(subset=['Check-in date']).reset_index(drop=True)

    # Convert to dates and sort it
    pivoted_df['Check-in date'] = pd.to_datetime(pivoted_df['Check-in date'], format='%m/%d/%Y', errors='raise')
    pivoted_df = pivoted_df.sort_values('Check-in date')

    pivoted_df['Check-in date'] = pivoted_df['Check-in date'].dt.strftime('%d-%m-%Y')
    pivoted_df['Check-out date'] = pd.to_datetime(pivoted_df['Check-out date'], format='%m/%d/%Y', errors='raise').dt.strftime('%d-%m-%Y')
    pivoted_df['Date of birth'] = pd.to_datetime(pivoted_df['Date of birth'], format='%m/%d/%Y', errors='raise').dt.strftime('%d-%m-%Y')

    # Replace NaN with empty strings and reset index
    pivoted_df.fillna('', inplace=True)
    pivoted_df = pivoted_df.reset_index(drop=True)

    return pivoted_df


def filter_df_on_checkin_date(clean_df, today=None):

    # Get today's date
    if not today:
        today = datetime.today().date()
        today = today.strftime('%d-%m-%Y')

    # Filter the DataFrame for check-in dates after today
    filtered_df = clean_df[clean_df['Check-in date'] == today]
    filtered_df = filtered_df.sort_values('Column_No')

    return filtered_df


def filter_df_on_name(clean_df, first_name=None, last_name=None):

    # Filter the DataFrame based on combinations of first and last name
    if first_name and last_name:
        filtered_df = clean_df[(clean_df['First name'] == first_name) & (clean_df['Last name'] == last_name)]
    elif first_name:
        filtered_df = clean_df[clean_df['First name'] == first_name]
    elif last_name:
        filtered_df = clean_df[clean_df['Last name'] == last_name]
    else:
        filtered_df = clean_df

    return filtered_df


def write_new_records_to_json(filtered_df, records_json='records.json'):

    if not object_exists(bucket_name, records_json):
        print('records.json file not found in S3 bucket.')
        return
    
    else:
        obj = download_object(bucket_name, records_json)
        records = json.loads(obj)

        previous_cum_df = pd.DataFrame(records[-1]['cum'])
        incr_df = filtered_df
        cum_df = pd.concat([previous_cum_df, incr_df]).drop_duplicates().reset_index(drop=True)

        new_dict = {
            'incr': incr_df.to_dict('records'),
            'cum': cum_df.to_dict('records')
        }

        records.append(new_dict)

        # Serialize the updated records list to a JSON string
        records_json_updated = json.dumps(records)

        # Save the updated JSON back to the S3 bucket
        s3.put_object(Bucket=bucket_name, Key=records_json, Body=records_json_updated)
        print(f"Updated records saved to {records_json} in S3 bucket '{bucket_name}'.")

        return


### Invoice processing functions ###
def get_latest_record(records_json='records.json'):

    if not object_exists(bucket_name, records_json):
        print('records.json file not found in S3 bucket.')
        return
    
    else:
        obj = download_object(bucket_name, records_json)
        records = json.loads(obj)

        last_cum_dict = records[-1]['cum']

        last_cum_df = pd.DataFrame(last_cum_dict)

        return last_cum_df


def filter_df_on_checkout_date(clean_df, today=None):

    # Get today's date
    if not today:
        today = datetime.today().date()
        today = today.strftime('%d-%m-%Y')

    # Filter the DataFrame for check-in dates after today
    filtered_df = clean_df[clean_df['Check-out date'] == today]

    return filtered_df


def convert_messages_to_df(emails_json='emails.json'):

    if not object_exists(bucket_name, emails_json):
        print('emails.json file not found in S3 bucket.')
        return
    
    else:
        obj = download_object(bucket_name, emails_json)
        messages = json.loads(obj)

        # Filter messages based on subject and sender criteria
        filtered_messages = [msg for msg in messages if "payout was sent" in msg["Subject"] and "airbnb" in msg["From"].lower()]

        # Create lists to store extracted data
        dates = []
        payout_amounts = []

        # Extract date and payout amount from filtered messages
        for msg in filtered_messages:
            date_str = msg["Date"]
            message = msg["Message"]

            # Update the regex to handle currency symbols, thousands separators, and decimal points
            amount_match = re.search(r'[\u20ac$£]?[,\d]+\.?\d*', message)
            if amount_match:
                # Remove any currency symbols and thousands separators before capturing the amount
                payout_amount = amount_match.group(0).replace(',', '').replace('\u20ac', '').replace('$', '').replace('£', '')
            else:
                payout_amount = None

            # Parse the date and format it as 'dd-mm-yyyy' while keeping it as a pd.datetime
            date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')
            dates.append(pd.to_datetime(date, format='%d-%m-%Y'))
            payout_amounts.append(payout_amount)

        # Create a DataFrame
        df = pd.DataFrame({
            "Date": dates,
            "Payout Amount": payout_amounts
        })

        # Sort the DataFrame by the 'Date' column
        df = df.sort_values(by='Date')

        # Convert Date column to string for better display
        df['Date'] = df['Date'].dt.strftime('%d-%m-%Y')

        # Display the sorted DataFrame
        return df


def get_first_payout_before_date(payout_df, today=None):

    # Get today's date
    if not today:
        today = datetime.today().date()

    if isinstance(today, str):
        today = pd.to_datetime(today, dayfirst=True).date()

    # Convert the 'Date' column of the DataFrame to datetime.date
    payout_df['Date'] = pd.to_datetime(payout_df['Date'], dayfirst=True).dt.date

    payout_df = payout_df.sort_values(by='Date')

    # Filter the DataFrame for check-in dates after today
    filtered_df = payout_df[payout_df['Date'] <= today]

    if filtered_df.empty:
        payout = payout_date = 'No payout found.'
    else:
        payout = str(filtered_df['Payout Amount'].iloc[-1])
        payout_date = str(filtered_df['Date'].iloc[-1])

    return payout, payout_date
