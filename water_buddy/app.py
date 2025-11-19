import streamlit as st
import requests
import json

# ---------------------------------------------------------
# FIREBASE SETTINGS
# ---------------------------------------------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"
USERS_NODE = "users"


# ---------------------------------------------------------
# FIREBASE FUNCTIONS
# ---------------------------------------------------------
def create_user(email, password, name):
    """Store new user in Firebase."""
    payload = {
        "email": email,
        "password": password,
        "name": name
    }
    url = f"{FIREBASE_URL}/{USERS_NODE}.json"
    r = requests.post(url, data=json.dumps(payload))
    return r.status_code == 200


def validate_login(email, password):
    """Verify user credentials in Firebase."""
    url = f"{FIREBASE_URL}/{USERS_NODE}.json"
    r = requests.get(url)

    if r.status_code != 200:
        return False, None

    users = r.json()

    if users:
        for uid, details in users.items():
            if details.get("email") == email and details.get("password") == password:
                return True, uid

    return False, None


def save_user_data(user_id, key, value):
    """Save user-specific data."""
    url = f"{FIREBASE_URL}/{USERS_NODE}/{user_id}/{key}.json"
    requests.put(url, data=json.dumps(value))


def get_user_data(user_id, key):
    """Retrieve user-specific field."""
    url = f"{FIREBASE_URL}/{USERS_NODE}/{user_id}/{key}.json"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None


# ---------------------------------------------------------
# STREAMLIT APP LAYOUT
# ---------------------------------------------------------
st.set_page_config(page_title="Hydration App", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "page" not in st.session_state:
    st.session_state.page = "login"


# ---------------------------------------------------------
# LOGIN PAGE
# ---------------------------------------------------------
def login_page():
    st.title("User Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    login_btn = st.button("Login")

    if login_btn:
        success, uid = validate_login(email, password)
        if success:
            st.session_state.logged_in = True
            st.session_state.user_id = uid
            st.success("Login successful.")
        else:
            st.error("Incorrect email or password.")

    st.write("New user?")
    if st.button("Go to Sign Up"):
        st.session_state.page = "signup"


# ---------------------------------------------------------
# SIGNUP PAGE
# ---------------------------------------------------------
def signup_page():
    st.title("Create Account")

    name = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    signup_btn = st.button("Sign Up")

    if signup_btn:
        created = create_user(email, password, name)
        if created:
            st.success("Account created successfully.")
            st.session_state.page = "login"
        else:
            st.error("Failed to create account. Try again.")

    if st.button("Back to Login"):
        st.session_state.page = "login"


# ---------------------------------------------------------
# LOGGED-IN DASHBOARD
# ---------------------------------------------------------
def dashboard():
    st.title("Hydration Dashboard")

    menu = st.sidebar.radio("Navigation", ["Home", "Log Water", "Logout"])

    if menu == "Home":
        st.subheader("Overview")

        current = get_user_data(st.session_state.user_id, "todays_water")
        if current is None:
            current = 0

        st.write(f"Water consumed today: {current} liters")

    elif menu == "Log Water":
        st.subheader("Record Today's Water Intake")
        value = st.number_input("Enter liters", min_value=0.0, step=0.1)

        if st.button("Save"):
            save_user_data(st.session_state.user_id, "todays_water", value)
            st.success("Saved successfully.")

    elif menu == "Logout":
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.page = "login"
        st.success("Logged out.")


# ---------------------------------------------------------
# PAGE ROUTING
# ---------------------------------------------------------
if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_page()
    else:
        login_page()
else:
    dashboard()
