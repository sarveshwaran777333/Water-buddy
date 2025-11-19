import streamlit as st
import requests
import json

# ---------------------------------------------------------
# FIREBASE SETTINGS (Realtime Database REST API)
# ---------------------------------------------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"
USERS_NODE = "users"


# ---------------------------------------------------------
# FIREBASE FUNCTIONS
# ---------------------------------------------------------
def firebase_write(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    r = requests.put(url, data=json.dumps(data))
    return r.status_code == 200


def firebase_push(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    r = requests.post(url, data=json.dumps(data))
    if r.status_code == 200:
        return True, r.json()
    return False, None


def firebase_read(path):
    url = f"{FIREBASE_URL}/{path}.json"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None


def create_user(username, password, name):
    payload = {
        "name": name,
        "username": username,
        "password": password,
        "todays_intake_ml": 0
    }
    return firebase_push(USERS_NODE, payload)[0]


def validate_login(username, password):
    all_users = firebase_read(USERS_NODE)

    if not all_users:
        return False, None

    for user_id, details in all_users.items():
        if details.get("username") == username and details.get("password") == password:
            return True, user_id

    return False, None


def update_user_intake(user_id, new_value):
    return firebase_write(f"{USERS_NODE}/{user_id}/todays_intake_ml", new_value)


def get_user_intake(user_id):
    data = firebase_read(f"{USERS_NODE}/{user_id}/todays_intake_ml")
    return data if data else 0


# ---------------------------------------------------------
# INITIAL STREAMLIT SESSION STATE
# ---------------------------------------------------------
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
    st.title("WaterBuddy – Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        success, user_id = validate_login(username, password)
        if success:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.success("Login successful")
        else:
            st.error("Invalid username or password")

    st.write("New user?")
    if st.button("Go to Sign Up"):
        st.session_state.page = "signup"


# ---------------------------------------------------------
# SIGNUP PAGE
# ---------------------------------------------------------
def signup_page():
    st.title("Create Account")

    name = st.text_input("Full Name")
    username = st.text_input("Choose a Username")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        created = create_user(username, password, name)
        if created:
            st.success("Account created successfully.")
            st.session_state.page = "login"
        else:
            st.error("Failed to create account.")

    if st.button("Back to Login"):
        st.session_state.page = "login"


# ---------------------------------------------------------
# DASHBOARD (LEFT PANE NAV, RIGHT PANE CONTENT)
# ---------------------------------------------------------
def dashboard():
    st.title("WaterBuddy Dashboard")

    # Create two columns: left = navigation, right = content
    left, right = st.columns([1, 3])

    with left:
        st.subheader("Navigation")
        page = st.radio("Go to", ["Home", "Log Water", "Logout"])

    with right:
        if page == "Home":
            st.subheader("Today's Hydration Summary")

            current_ml = get_user_intake(st.session_state.user_id)

            st.write(f"Total consumed today: {current_ml} ml")

            goal = 2500
            percent = min(round((current_ml / goal) * 100, 2), 100)

            st.progress(percent / 100)

            if percent < 30:
                st.info("Keep going, stay hydrated.")
            elif percent < 70:
                st.success("Great progress!")
            elif percent < 100:
                st.success("Almost there!")
            else:
                st.success("Goal achieved!")

        elif page == "Log Water":
            st.subheader("Log Water Intake")

            current_ml = get_user_intake(st.session_state.user_id)

            add = st.number_input("Add Amount (ml)", min_value=0, step=50)

            if st.button("Add"):
                new_value = current_ml + add
                update_user_intake(st.session_state.user_id, new_value)
                st.success("Water logged successfully.")

        elif page == "Logout":
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.page = "login"
            st.success("Logged out.")


# ---------------------------------------------------------
# ROUTING
# ---------------------------------------------------------
if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_page()
    else:
        login_page()
else:
    dashboard()
