import streamlit as st
import pandas as pd
import importlib
import json
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
if 'invoice_df' not in st.session_state:
    st.session_state.invoice_df = pd.DataFrame()
if 'invoice_completed' not in st.session_state:
    st.session_state.invoice_completed = False

# Initialize other variables
nif = None
# invoice_df = pd.DataFrame()

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

# Reset invoice_df if needed
if st.button('Fetch guest details'):
    st.session_state.invoice_df = pd.DataFrame()

# Get guest's details
if not st.session_state.clean_df.empty:
    invoice_df = data_processing.filter_df_on_checkout_date(st.session_state.clean_df, checkout_date)

    # Filter and assign to session state
    if st.session_state.invoice_df.empty:
        st.session_state.invoice_df = invoice_df[['First name', 
                                                  'Last name', 
                                                  'Check-in date', 
                                                  'Check-out date', 
                                                  'Passport (or ID) number', 
                                                  'Country of residence']].head(1)
# Get list of countries
with open('parameters/countries_mapping.json') as f:
    countries = json.load(f)
countries_list = list(countries.keys())

# Display the guest's details in two columns    
st.subheader('Details on the invoice:')
col1, col2 = st.columns(2)
with col1:
    first_name = st.text_input('First name:', value=st.session_state.invoice_df['First name'].values[0] if not st.session_state.invoice_df.empty else '')
    checkin_date = st.date_input('Check-in date:', format="DD-MM-YYYY", value=pd.to_datetime(st.session_state.invoice_df['Check-in date'].values[0], dayfirst=True) if not st.session_state.invoice_df.empty else pd.to_datetime("today"))
    invoice_date = st.date_input('Invoice date:', format="DD-MM-YYYY", value=pd.to_datetime(checkout_date, dayfirst=True))
    passport = st.text_input('Passport number:', value=st.session_state.invoice_df['Passport (or ID) number'].values[0] if not st.session_state.invoice_df.empty else '')
with col2:
    last_name = st.text_input('Last name:', value=st.session_state.invoice_df['Last name'].values[0] if not st.session_state.invoice_df.empty else '')
    checkout_date = st.date_input('Check-out date:', format="DD-MM-YYYY", value=pd.to_datetime(st.session_state.invoice_df['Check-out date'].values[0], dayfirst=True) if not st.session_state.invoice_df.empty else pd.to_datetime("today"))
    # country = st.text_input('Country of residence:', value=st.session_state.invoice_df['Country of residence'].values[0] if not st.session_state.invoice_df.empty else '')
    country = st.selectbox('Country of residence:', countries_list, index=countries_list.index(st.session_state.invoice_df['Country of residence'].values[0]) if not st.session_state.invoice_df.empty else 0)
    if country == 'Portugal':
        nif = st.text_input('NIF:')

# with col1:
#     first_name = st.text_input('First name:', value=invoice_df['First name'].values[0] if not invoice_df.empty else '')
#     checkin_date = st.date_input('Check-in date:', format="DD-MM-YYYY", value=pd.to_datetime(invoice_df['Check-in date'].values[0], dayfirst=True) if not invoice_df.empty else pd.to_datetime("today"))
#     invoice_date = st.date_input('Invoice date:', format="DD-MM-YYYY", value=pd.to_datetime(checkout_date, dayfirst=True))
#     passport = st.text_input('Passport number:', value=invoice_df['Passport (or ID) number'].values[0] if not invoice_df.empty else '')
# with col2:
#     last_name = st.text_input('Last name:', value=invoice_df['Last name'].values[0] if not invoice_df.empty else '')
#     checkout_date = st.date_input('Check-out date:', format="DD-MM-YYYY", value=pd.to_datetime(invoice_df['Check-out date'].values[0], dayfirst=True) if not invoice_df.empty else pd.to_datetime("today"))
#     country = st.text_input('Country of residence:', value=invoice_df['Country of residence'].values[0] if not invoice_df.empty else '')
#     if country == 'Portugal':
#         nif = st.text_input('NIF:')

if st.button('Overwrite details'):
    # Put the details in the DataFrame
    st.session_state.invoice_df = pd.DataFrame(columns=['First name', 'Last name', 'Check-in date', 'Check-out date', 'Passport (or ID) number', 'Country of residence'])
    st.session_state.invoice_df.loc[0, 'First name'] = first_name
    st.session_state.invoice_df.loc[0, 'Last name'] = last_name
    st.session_state.invoice_df.loc[0, 'Check-in date'] = checkin_date.strftime('%d-%m-%Y')
    st.session_state.invoice_df.loc[0, 'Check-out date'] = checkout_date.strftime('%d-%m-%Y')
    st.session_state.invoice_df.loc[0, 'Passport (or ID) number'] = passport
    st.session_state.invoice_df.loc[0, 'Country of residence'] = country

    # invoice_df.loc[0, 'First name'] = first_name
    # invoice_df.loc[0, 'Last name'] = last_name
    # invoice_df.loc[0, 'Check-in date'] = checkin_date.strftime('%d-%m-%Y')
    # invoice_df.loc[0, 'Check-out date'] = checkout_date.strftime('%d-%m-%Y')
    # invoice_df.loc[0, 'Passport (or ID) number'] = passport
    # invoice_df.loc[0, 'Country of residence'] = country

# Display the updated DataFrame
st.session_state.invoice_df = st.data_editor(st.session_state.invoice_df, hide_index=True)


# Handle NIF input
nif_condition = not st.session_state.invoice_df.empty and st.session_state.invoice_df[['Country of residence']].values[0][0] == 'Portugal'


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

    if nif_condition and (len(nif) != 9 and len(nif) != 0):
        st.error('Please enter a valid NIF or leave blank.')
    else:
        # Reset completion state
        st.session_state.invoice_completed = False
        message_placeholder = st.empty()

        # Run invoice automation with the adapted callback
        invoice_callback = lambda message: update_invoice_ui(message, message_placeholder)
        web_automation.fill_in_invoice(invoice_callback, 
                                       st.session_state.invoice_df, 
                                       invoice_amount, 
                                       invoice_date, 
                                       nif)
    
        if st.session_state.invoice_completed:
            st.success('Invoice issued successfully!')
        else:
            st.error('Invoice has not been issued.')
