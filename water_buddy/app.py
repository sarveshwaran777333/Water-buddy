import streamlit as st
import requests
import json

# ----------------------------------------------------------------
# FIREBASE CONFIG
# ----------------------------------------------------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"
USERS_NODE = "users"

# ----------------------------------------------------------------
# FIREBASE FUNCTIONS
# ----------------------------------------------------------------
def signup_user(email, password):
    payload = {
        "email": email,
        "password": password
    }
    url = f"{FIREBASE_URL}/{USERS_NODE}.json"
    response = requests.post(url, data=json.dumps(payload))
    return response.status_code == 200

def login_user(email, password):
    url = f"{FIREBASE_URL}/{USERS_NODE}.json"
    response = requests.get(url)

    if response.status_code != 200:
        return False, None

    data = response.json()

    if data:
        for user_id, user_data in data.items():
            if user_data.get("email") == email and user_data.get("password") == password:
                return True, user_id
    return False, None

def save_user_data(user_id, key, value):
    url = f"{FIREBASE_URL}/{USERS_NODE}/{user_id}/{key}.json"
    requests.put(url, data=json.dumps(value))

def get_user_data(user_id, key):
    url = f"{FIREBASE_URL}/{USERS_NODE}/{user_id}/{key}.json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# ----------------------------------------------------------------
# APP UI
# ----------------------------------------------------------------
st.set_page_config(page_title="Water Hydrator", layout="wide")

# Track login status
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ----------------------------------------------------------------
# LOGIN PAGE
# ----------------------------------------------------------------
def login_page():
    st.title("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        success, user_id = login_user(email, password)
        if success:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.success("Login Successful")
        else:
            st.error("Invalid email or password")

    st.write("Not registered?")
    if st.button("Go to Signup"):
        st.session_state.page = "signup"


# ----------------------------------------------------------------
# SIGNUP PAGE
# ----------------------------------------------------------------
def signup_page():
    st.title("Sign Up")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        if signup_user(email, password):
            st.success("Account created successfully.")
            st.session_state.page = "login"
        else:
            st.error("Signup failed. Try again.")

    if st.button("Back to Login"):
        st.session_state.page = "login"


# ----------------------------------------------------------------
# MAIN DASHBOARD
# ----------------------------------------------------------------
def dashboard():
    st.title("Water Hydrator Dashboard")

    # LEFT NAVIGATION PANEL
    menu = st.sidebar.radio("Navigation", ["Home", "Daily Intake", "Statistics", "Logout"])

    # HOME PAGE
    if menu == "Home":
        st.subheader("Welcome to your Dashboard")

        liters_today = get_user_data(st.session_state.user_id, "liters_today")
        if liters_today is None:
            liters_today = 0

        st.write(f"Current Water Intake Today: {liters_today} liters")

    # DAILY INTAKE PAGE
    elif menu == "Daily Intake":
        st.subheader("Log Water Intake")

        liters = st.number_input("Enter Liters", min_value=0.0, step=0.1)

        if st.button("Save"):
            save_user_data(st.session_state.user_id, "liters_today", liters)
            st.success("Saved Successfully")

    # STATISTICS PAGE
    elif menu == "Statistics":
        st.subheader("Your Stats")

        liters_today = get_user_data(st.session_state.user_id, "liters_today") or 0
        st.write(f"Water consumed today: {liters_today} liters")

    # LOGOUT
    elif menu == "Logout":
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.success("Logged Out Successfully")


# ----------------------------------------------------------------
# PAGE ROUTING
# ----------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "login"

if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_page()
    else:
        login_page()
else:
    dashboard()
