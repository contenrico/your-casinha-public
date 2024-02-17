import hmac
import streamlit as st

st.session_state.authenticated = False

# Password protection
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

if check_password():

    st.session_state.authenticated = True

    ## MAIN PAGE ##
    st.set_page_config(page_title="Hello", page_icon="👋")
    st.write("# 🏠 Your Casinha in Rua Marvila")
    st.sidebar.success("Select a task above.")
    st.markdown(
        """
        Welcome to the admin dashboard for Your Casinha in Rua Marvila! \n
        **👈 Select a task from the sidebar** to run the appropriate task for your Airbnb.
        """
    )