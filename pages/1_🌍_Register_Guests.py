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
if 'filtered_df' not in st.session_state:
    st.session_state.filtered_df = pd.DataFrame()
if 'update_message' not in st.session_state:
    st.session_state.update_message = "Click the button to start the process..."
if 'sef_completed' not in st.session_state:
    st.session_state.sef_completed = False

### --- GET AND DISPLAY FORM RESPONSES --- ###

# Add input field with today's date by default
checkin_date = st.date_input('Check-in date: ', value=pd.to_datetime("today"), format="DD-MM-YYYY")
checkin_date = checkin_date.strftime('%d-%m-%Y')

if st.button('Get form responses'):
    # Get form responses
    sheet_path = google_api.get_form()
    clean_df = data_processing.clean_sheet()
    filtered_df = data_processing.filter_df_on_checkin_date(clean_df, checkin_date)

    # Filter and assign to session state - TODO get these columns to be displayed, but keep all of them in df
    st.session_state.filtered_df = filtered_df[['First name', 'Last name', 
                                                'Check-in date', 'Check-out date',
                                                'Date of birth', 'Nationality', 'City of birth',
                                                'City of residence', 'Country of residence',
                                                'Passport (or ID) number', 'Country of issue']]

# Editable DataFrame
st.session_state.filtered_df = st.data_editor(st.session_state.filtered_df, hide_index=True)

### --- REGISTER GUESTS ON SEF --- ###

# Define a callback function to update the UI and track completion
def update_ui(message):
    st.session_state.update_message = message
    # Check if the process has completed successfully
    if message == "SEF registration completed successfully.":
        st.session_state.sef_completed = True
    else:
        st.session_state.sef_completed = False

# if st.button('Register guests on SEF'): 
#     #TODO validate check-in and check-out dates, specifically if check-in is after today, can't click
#     # Run SEF automation
#     message = web_automation.fill_in_sef_form(st.session_state.filtered_df)

#     # Write records to json if successful
#     if message == 'SEF Completed':
#         data_processing.write_new_records_to_json(st.session_state.filtered_df)
#         st.success('Guests registered successfully!')

# Displaying the update message dynamically
message_placeholder = st.empty()
message_placeholder.text(st.session_state.update_message)

# TODO: TEST FUNCTION ALONE AS IT'S NOT WORKING 
if st.button('Register guests on SEF'): #TODO validate check-in and check-out dates, specifically if check-in is after today, can't click
    # Reset completion state
    st.session_state.sef_completed = False
    # Run SEF automation with the adapted callback
    web_automation.fill_in_sef_form(df=st.session_state.filtered_df, callback=update_ui)
    # After completion, check if it was successful
    if st.session_state.sef_completed:
        # data_processing.write_new_records_to_json(st.session_state.filtered_df)
        st.success('Guests registered successfully!')
    else:
        st.error('SEF registration failed.')