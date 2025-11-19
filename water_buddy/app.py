import streamlit as st
import requests
import json
from datetime import date
import random

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"
USERS_NODE = "users"
DATE_STR = date.today().isoformat()

AGE_GOALS_ML = {
    "6-12": 1600,
    "13-18": 2000,
    "19-50": 2500,
    "65+": 2000,
}

DEFAULT_QUICK_LOG_ML = 250
CUPS_TO_ML = 236.588

TIPS = [
    "Keep a water bottle visible.",
    "Drink one glass before every meal.",
    "Hydration helps concentration.",
    "Small sips throughout the day help best.",
]

# -------------------------------------------------
# Firebase Helpers
# -------------------------------------------------
def firebase_read(path):
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        st.error("Network error while reading Firebase.")
        return None

def firebase_patch(path, value_dict):
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        r = requests.patch(url, data=json.dumps(value_dict))
        return r.status_code == 200
    except:
        return False

def firebase_post(path, value_dict):
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        r = requests.post(url, data=json.dumps(value_dict))
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None


# -------------------------------------------------
# User Management
# -------------------------------------------------
def find_user_by_username(username):
    all_users = firebase_read(USERS_NODE)
    if not all_users:
        return None, None
    for uid, record in all_users.items():
        if record.get("username") == username:
            return uid, record
    return None, None

def create_user(username, password):
    existing_uid, _ = find_user_by_username(username)
    if existing_uid:
        return None

    payload = {
        "username": username,
        "password": password,
        "created_at": DATE_STR,
        "profile": {
            "age_group": "19-50",
            "user_goal_ml": AGE_GOALS_ML["19-50"],
        }
    }
    res = firebase_post(USERS_NODE, payload)
    return res.get("name") if res else None

def validate_login(username, password):
    uid, record = find_user_by_username(username)
    if uid and record.get("password") == password:
        return True, uid
    return False, None


# -------------------------------------------------
# Daily Intake Helpers
# -------------------------------------------------
def get_today_intake(uid):
    path = f"{USERS_NODE}/{uid}/days/{DATE_STR}/intake"
    val = firebase_read(path)
    return val if isinstance(val, int) else 0

def set_today_intake(uid, value):
    path = f"{USERS_NODE}/{uid}/days/{DATE_STR}"
    return firebase_patch(path, {"intake": value})

def reset_today(uid):
    return set_today_intake(uid, 0)

def get_user_profile(uid):
    profile = firebase_read(f"{USERS_NODE}/{uid}/profile")
    if not profile:
        return {
            "age_group": "19-50",
            "user_goal_ml": AGE_GOALS_ML["19-50"]
        }
    return profile

def update_user_profile(uid, new_data):
    path = f"{USERS_NODE}/{uid}/profile"
    return firebase_patch(path, new_data)

def get_username(uid):
    rec = firebase_read(f"{USERS_NODE}/{uid}")
    return rec.get("username", "User")


# -------------------------------------------------
# Streamlit Layout Setup
# -------------------------------------------------
st.set_page_config(page_title="WaterBuddy", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "uid" not in st.session_state:
    st.session_state.uid = None

if "page" not in st.session_state:
    st.session_state.page = "login"


# -------------------------------------------------
# LOGIN PAGE
# -------------------------------------------------
def login_page():
    st.title("WaterBuddy Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        ok, uid = validate_login(username.strip(), password)
        if ok:
            st.session_state.logged_in = True
            st.session_state.uid = uid
            st.session_state.page = "dashboard"
            st.success("Login successful.")
            st.experimental_rerun()
        else:
            st.error("Incorrect username or password")

    if st.button("Create new account"):
        st.session_state.page = "signup"
        st.experimental_rerun()


# -------------------------------------------------
# SIGNUP PAGE
# -------------------------------------------------
def signup_page():
    st.title("Create WaterBuddy Account")

    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")

    if st.button("Register"):
        if username.strip() == "" or password.strip() == "":
            st.error("Username and password cannot be empty.")
            return

        uid = create_user(username.strip(), password)
        if uid:
            st.success("Account created successfully.")
            st.session_state.page = "login"
        else:
            st.error("Username already exists. Try another.")

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.experimental_rerun()


# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
def dashboard():
    uid = st.session_state.uid
    profile = get_user_profile(uid)
    today_intake = get_today_intake(uid)

    left, right = st.columns([1, 3])

    with left:
        st.header("Menu")
        choice = st.radio("Navigation", ["Home", "Log Water", "Settings", "Logout"])

    with right:

        # HOME PAGE
        if choice == "Home":
            st.title("Today’s Progress")

            standard = AGE_GOALS_ML[profile["age_group"]]
            user_goal = profile.get("user_goal_ml", standard)

            percent = min((today_intake / user_goal) * 100, 100)

            st.metric("Today's Intake", f"{today_intake} ml")

            st.progress(percent / 100)

            if percent >= 100:
                st.success("Great job! You've hit your hydration goal!")
            elif percent >= 50:
                st.info("Halfway there — keep sipping!")
            else:
                st.write("You can do it — hydration boosts energy.")

        # LOG WATER PAGE
        elif choice == "Log Water":
            st.title("Log Water")

            st.write(f"Current intake: {today_intake} ml")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button(f"+{DEFAULT_QUICK_LOG_ML} ml"):
                    set_today_intake(uid, today_intake + DEFAULT_QUICK_LOG_ML)
                    st.experimental_rerun()

            with col2:
                custom = st.number_input("Enter custom amount (ml)", min_value=0)
                if st.button("Add custom"):
                    set_today_intake(uid, today_intake + custom)
                    st.experimental_rerun()

            with col3:
                if st.button("Reset today"):
                    reset_today(uid)
                    st.experimental_rerun()

        # SETTINGS PAGE
        elif choice == "Settings":
            st.title("Settings")

            age_group = st.selectbox("Select Age Group", list(AGE_GOALS_ML.keys()), index=list(AGE_GOALS_ML.keys()).index(profile["age_group"]))
            suggested = AGE_GOALS_ML[age_group]
            user_goal_val = st.number_input("Daily Goal (ml)", min_value=500, value=profile.get("user_goal_ml", suggested))

            if st.button("Save"):
                update_user_profile(uid, {"age_group": age_group, "user_goal_ml": user_goal_val})
                st.success("Settings updated.")

        # LOGOUT
        elif choice == "Logout":
            st.session_state.logged_in = False
            st.session_state.uid = None
            st.session_state.page = "login"
            st.experimental_rerun()


# -------------------------------------------------
# PAGE ROUTING
# -------------------------------------------------
if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_page()
    else:
        login_page()
else:
    dashboard()
