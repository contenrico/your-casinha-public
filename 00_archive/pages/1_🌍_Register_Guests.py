import streamlit as st
import pandas as pd
import importlib
from scripts import google_api, web_automation, data_processing

importlib.reload(google_api)
importlib.reload(web_automation)
importlib.reload(data_processing)

if not st.session_state.authenticated:
    st.error('Please enter your password in the first page.')
    st.stop()  # Do not continue if check_password is not True.

# Configure the page
st.set_page_config(page_title="Register Guests", page_icon="🌍")
st.title('Register New Guests')

# Initialize session state variables
if 'filtered_sef_df' not in st.session_state:
    st.session_state.filtered_sef_df = pd.DataFrame()
if 'sef_completed' not in st.session_state:
    st.session_state.sef_completed = False

### --- GET AND DISPLAY FORM RESPONSES --- ###
    
# Create a checkbox and check its state
search_by_name = st.checkbox('Search by name')

# Initialize input names
first_name = ''
last_name = ''

# If the checkbox is ticked, show the input fields
if search_by_name:
    # Create two columns
    col1, col2 = st.columns(2)

    # Add input field with name
    with col1:
        first_name = st.text_input('First name: ')
    with col2:
        last_name = st.text_input('Last name: ')
else:
    # Add input field with today's date by default
    checkin_date = st.date_input('Check-in date: ', value=pd.to_datetime("today"), format="DD-MM-YYYY")
    checkin_date = checkin_date.strftime('%d-%m-%Y')

if st.button('Get form responses'):
    # Get form responses
    sheet_path = google_api.get_form()
    clean_df = data_processing.clean_sheet()

    # Filter df based on check-in date only if name is empty
    if first_name == '' and last_name == '':
        filtered_sef_df = data_processing.filter_df_on_checkin_date(clean_df, checkin_date)
    else:
        # Filter df based on name
        filtered_sef_df = data_processing.filter_df_on_name(clean_df, first_name, last_name)

    # Filter and assign to session state - TODO get these columns to be displayed, but keep all of them in df
    st.session_state.filtered_sef_df = filtered_sef_df[['First name', 'Last name', 
                                                'Check-in date', 'Check-out date',
                                                'Date of birth', 'Nationality', 'City of birth',
                                                'City of residence', 'Country of residence',
                                                'Passport (or ID) number', 'Country of issue']]

# Editable DataFrame
st.session_state.filtered_sef_df = st.data_editor(st.session_state.filtered_sef_df, hide_index=True)

### --- REGISTER GUESTS ON SEF --- ###

# Define a callback function to update the UI and track completion
def update_sef_ui(message, placeholder=None):

    if placeholder is not None:
        placeholder.text(message)

    # Check if the process has completed successfully
    if message == "Done.":
        st.session_state.sef_completed = True
    else:
        st.session_state.sef_completed = False

if st.button('Register guests on SEF'): #TODO validate check-in and check-out dates, specifically if check-in is after today, can't click
    # Reset completion state
    st.session_state.sef_completed = False
    message_placeholder = st.empty()

    # Run SEF automation with the adapted callback
    sef_callback = lambda message: update_sef_ui(message, message_placeholder)
    web_automation.fill_in_sef_form(df=st.session_state.filtered_sef_df, callback=sef_callback)

    # After completion, check if it was successful
    if st.session_state.sef_completed:
        data_processing.write_new_records_to_json(st.session_state.filtered_sef_df)
        st.success('Guests registered successfully!')
    else:
        st.error('SEF registration failed.')