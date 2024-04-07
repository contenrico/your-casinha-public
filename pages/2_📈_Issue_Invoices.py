import streamlit as st
import pandas as pd
import importlib
import os
from scripts import google_api, web_automation, data_processing

importlib.reload(google_api)
importlib.reload(web_automation)
importlib.reload(data_processing)

if not st.session_state.authenticated:
    st.error('Please enter your password in the first page.')
    st.stop()  # Do not continue if check_password is not True.

# Configure the page
st.set_page_config(page_title="Issue Invoices", page_icon="📈")
st.title('Issue New Invoices')

# Initialize session state for the DataFrame
if 'payout_df' not in st.session_state:
    st.session_state.payout_df = pd.DataFrame()
if 'clean_df' not in st.session_state:
    st.session_state.clean_df = pd.DataFrame()
if 'filtered_df' not in st.session_state:
    st.session_state.filtered_df = pd.DataFrame()
if 'invoice_completed' not in st.session_state:
    st.session_state.invoice_completed = False

# Initialize other variables
nif = None

# Add input field with today's date by default
checkout_date = st.date_input('Check-out date: ', value=pd.to_datetime("today"), format="DD-MM-YYYY")
checkout_date = checkout_date.strftime('%d-%m-%Y')

if st.button('Get payout amounts'):

    st.session_state.clean_df = data_processing.get_latest_record()

    # Get emails and display dataframe of payouts
    emails_json = google_api.get_emails()
    st.session_state.payout_df = data_processing.convert_messages_to_df()

# Display latest payout amount and make amount editable
st.dataframe(st.session_state.payout_df, hide_index=True)

if not st.session_state.payout_df.empty:
    invoice_amount, payout_date = data_processing.get_first_payout_before_date(st.session_state.payout_df, checkout_date)
    if invoice_amount == 'No payout found.':
        st.error('No payout found for this date.')
    else:
        invoice_amount = st.number_input('Invoice amount based on selected check-out date:', value=float(invoice_amount))

# Get guest's details
if not st.session_state.clean_df.empty:
    filtered_df = data_processing.filter_df_on_checkout_date(st.session_state.clean_df, checkout_date)

    # Filter and assign to session state - TODO get these columns to be displayed, but keep all of them in df
    st.session_state.filtered_df = filtered_df[['First name', 'Last name', 
                                                'Check-in date', 'Check-out date',
                                                'Date of birth', 'Nationality', 'City of birth',
                                                'City of residence', 'Country of residence',
                                                'Passport (or ID) number', 'Country of issue']]
    st.subheader('Details on the invoice:')
    invoice_date = st.date_input('Invoice date:', value=pd.to_datetime(checkout_date, dayfirst=True), format="DD-MM-YYYY")
    st.session_state.filtered_df = st.data_editor(st.session_state.filtered_df.head(1), hide_index=True)

# Allow for NIF input
nif_condition = not st.session_state.filtered_df.empty and st.session_state.filtered_df[['Country of residence']].values[0][0] == 'Portugal'
if nif_condition:
    nif = st.text_input('NIF:')

### --- ISSUE INVOICE --- ###
    
# Define a callback function to update the UI and track completion
def update_invoice_ui(message, placeholder=None):

    if placeholder is not None:
        placeholder.text(message)

    # Check if the process has completed successfully
    if message == "Done.":
        st.session_state.invoice_completed = True
    else:
        st.session_state.invoice_completed = False

# Run automation to issue invoice
if st.button('Issue invoice'):
    if nif_condition and len(nif) != 9:
        st.error('Please enter a valid NIF.')
    else:
        # Reset completion state
        st.session_state.invoice_completed = False
        message_placeholder = st.empty()

        # Run invoice automation with the adapted callback
        callback = lambda message: update_invoice_ui(message, message_placeholder)
        web_automation.fill_in_invoice(callback, 
                                       st.session_state.filtered_df, 
                                       invoice_amount, 
                                       invoice_date, 
                                       nif)
    
        if st.session_state.invoice_completed:
            st.success('Invoice issued successfully!')
        else:
            st.error('Invoice has not been issued.')
