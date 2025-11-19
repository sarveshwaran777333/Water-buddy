import streamlit as st
import random
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------------------------------------
# INITIALIZE FIREBASE
# -------------------------------------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -------------------------------------------------------
# SESSION VARIABLES
# -------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

# -------------------------------------------------------
# FIREBASE FUNCTIONS
# -------------------------------------------------------
def firebase_create_user(username, password):
    ref = db.collection("users").document(username)
    if ref.get().exists:
        return False
    ref.set({"password": password})
    return True

def firebase_validate_user(username, password):
    ref = db.collection("users").document(username).get()
    if ref.exists and ref.to_dict().get("password") == password:
        return True
    return False

def firebase_log_water(username, ml):
    today = datetime.date.today().isoformat()
    ref = db.collection("users").document(username).collection("days").document(today)

    doc = ref.get()
    if doc.exists:
        current = doc.to_dict().get("intake", 0)
        ref.set({"intake": current + ml}, merge=True)
    else:
        ref.set({"intake": ml})

def firebase_reset_day(username):
    today = datetime.date.today().isoformat()
    ref = db.collection("users").document(username).collection("days").document(today)
    ref.set({"intake": 0})

def firebase_get_today_intake(username):
    today = datetime.date.today().isoformat()
    ref = db.collection("users").document(username).collection("days").document(today).get()
    if ref.exists:
        return ref.to_dict().get("intake", 0)
    return 0

# -------------------------------------------------------
# LOGIN PAGE
# -------------------------------------------------------
def page_login():
    st.title("WaterBuddy – Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if firebase_validate_user(user, pwd):
            st.session_state.logged_in = True
            st.session_state.username = user
        else:
            st.error("Invalid credentials.")

    if st.button("Create New Account"):
        st.session_state.current_page = "Signup"

# -------------------------------------------------------
# SIGNUP PAGE
# -------------------------------------------------------
def page_signup():
    st.title("Create a WaterBuddy Account")

    new_user = st.text_input("Choose Username")
    new_pass = st.text_input("Create Password", type="password")

    if st.button("Create Account"):
        if firebase_create_user(new_user, new_pass):
            st.success("Account created. Please log in.")
            st.session_state.current_page = "Login"
        else:
            st.error("Username already exists.")

    if st.button("Back to Login"):
        st.session_state.current_page = "Login"

# -------------------------------------------------------
# LEFT NAVIGATION PANE
# -------------------------------------------------------
def nav_sidebar():
    with st.sidebar:
        st.title("WaterBuddy")
        choices = ["Home", "Log Water", "Progress", "Profile", "Logout"]
        selection = st.radio("Navigate", choices)

        st.session_state.current_page = selection

# -------------------------------------------------------
# MAIN: HOME PAGE
# -------------------------------------------------------
def page_home():
    st.header(f"Hello, {st.session_state.username}!")
    st.write("Welcome to your personal hydration tracker.")
    st.write("Use the left panel to navigate.")

# -------------------------------------------------------
# LOG WATER PAGE
# -------------------------------------------------------
def page_log():
    st.header("Water Intake Logging")

    # Age-based recommended goals
    standard_goals = {
        "6–12": 1600,
        "13–18": 1800,
        "19–50": 2500,
        "65+": 2000,
    }

    st.subheader("Select Age Group")
    age_group = st.selectbox("Age Range", standard_goals.keys())
    default_goal = standard_goals[age_group]

    st.write(f"Suggested Goal: {default_goal} ml")

    daily_goal = st.number_input(
        "Adjust Daily Goal (optional)",
        min_value=500,
        max_value=5000,
        value=default_goal,
        step=50
    )

    st.subheader("Add Water Intake")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("+250 ml"):
            firebase_log_water(st.session_state.username, 250)

    with col2:
        custom = st.number_input("Enter custom amount (ml):", 0, 2000, 0, 50)
        if st.button("Add"):
            firebase_log_water(st.session_state.username, custom)

    if st.button("Reset Today"):
        firebase_reset_day(st.session_state.username)

    intake = firebase_get_today_intake(st.session_state.username)
    remaining = max(0, daily_goal - intake)
    percentage = min(100, int((intake / daily_goal) * 100))

    st.write(f"Water consumed today: {intake} ml")
    st.write(f"Remaining: {remaining} ml")

    st.progress(percentage / 100)

    if percentage < 25:
        st.info("Good start. Keep going.")
    elif percentage < 50:
        st.info("Nice progress.")
    elif percentage < 75:
        st.success("Great! Halfway completed.")
    elif percentage < 100:
        st.success("Almost there!")
    else:
        st.success("Goal achieved!")

# -------------------------------------------------------
# PROGRESS PAGE
# -------------------------------------------------------
def page_progress():
    st.header("Daily Progress Report")

    intake = firebase_get_today_intake(st.session_state.username)
    st.write(f"Today’s total intake: {intake} ml")

    tips = [
        "Carry a bottle everywhere.",
        "Start your day with a glass of water.",
        "Hydration improves focus and memory.",
        "Drinking water boosts metabolism.",
        "Your brain works better when hydrated."
    ]
    st.subheader("Hydration Tip")
    st.write(random.choice(tips))

# -------------------------------------------------------
# PROFILE PAGE
# -------------------------------------------------------
def page_profile():
    st.header("Profile Information")
    st.write(f"Username: {st.session_state.username}")
    st.write("Data stored securely in Firebase Firestore.")

# -------------------------------------------------------
# LOGOUT
# -------------------------------------------------------
def page_logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.current_page = "Login"

# -------------------------------------------------------
# APPLICATION FLOW
# -------------------------------------------------------
if not st.session_state.logged_in:
    if st.session_state.current_page == "Signup":
        page_signup()
    else:
        page_login()

else:
    nav_sidebar()

    if st.session_state.current_page == "Home":
        page_home()
    elif st.session_state.current_page == "Log Water":
        page_log()
    elif st.session_state.current_page == "Progress":
        page_progress()
    elif st.session_state.current_page == "Profile":
        page_profile()
    elif st.session_state.current_page == "Logout":
        page_logout()
