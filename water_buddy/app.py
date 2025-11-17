import streamlit as st
import requests
import hashlib
import datetime
import random

# --------------------------
# FIREBASE CONFIG
# --------------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"   # ← replace this


# --------------------------
# PASSWORD HASHING
# --------------------------
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


# --------------------------
# FIREBASE FUNCTIONS
# --------------------------
def firebase_signup(username, password_hash):
    url = f"{FIREBASE_URL}/users/{username}.json"
    data = {"password": password_hash}
    requests.put(url, json=data)


def firebase_user_exists(username):
    url = f"{FIREBASE_URL}/users/{username}.json"
    res = requests.get(url).json()
    return res is not None


def firebase_check_password(username, password_hash):
    url = f"{FIREBASE_URL}/users/{username}/password.json"
    res = requests.get(url).json()
    return res == password_hash


def save_user_data(username, data):
    url = f"{FIREBASE_URL}/data/{username}.json"
    requests.put(url, json=data)


def load_user_data(username):
    url = f"{FIREBASE_URL}/data/{username}.json"
    res = requests.get(url).json()
    return res


# --------------------------
# WATERBUDDY DEFAULT SETTINGS
# --------------------------
AGE_GROUP_GOALS = {
    "6-12": 1600,
    "13-18": 2000,
    "19-50": 2500,
    "51-64": 2400,
    "65+": 2200
}

QUICK_LOG = 250
CUP_ML = 240

TIPS = [
    "Sip water every 30 minutes.",
    "Start your day with a glass of water!",
    "Carry a bottle everywhere.",
    "Water improves mood & focus.",
    "Staying hydrated keeps you energetic."
]


# --------------------------
# INITIALIZE SESSION
# --------------------------
def init_user_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if "username" not in st.session_state:
        st.session_state.username = ""

    if "water_data" not in st.session_state:
        st.session_state.water_data = {
            "date": str(datetime.date.today()),
            "age_group": "19-50",
            "daily_goal": 2500,
            "intake": 0,
            "logs": [],
        }


# --------------------------
# LOGIN PAGE
# --------------------------
def login_page():
    st.title("🔐 Login to WaterBuddy")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if not firebase_user_exists(username):
            st.error("User does not exist!")
            return

        if firebase_check_password(username, hash_password(password)):
            st.success("Login successful!")
            st.session_state.logged_in = True
            st.session_state.username = username

            # load personal saved data
            saved = load_user_data(username)
            if saved:
                st.session_state.water_data = saved

            st.experimental_rerun()
        else:
            st.error("Incorrect password!")


# --------------------------
# SIGNUP PAGE
# --------------------------
def signup_page():
    st.title("🆕 Create WaterBuddy Account")

    username = st.text_input("Choose Username")
    password = st.text_input("Create Password", type="password")
    cpassword = st.text_input("Confirm Password", type="password")

    if st.button("Sign Up"):
        if firebase_user_exists(username):
            st.error("Username already taken!")
            return

        if password != cpassword:
            st.error("Passwords do not match.")
            return

        firebase_signup(username, hash_password(password))
        st.success("Account created! Please login.")


# --------------------------
# WATERBUDDY MAIN APP
# --------------------------
def waterbuddy_app():
    st.title("💧 WaterBuddy – Your Hydration Partner")

    data = st.session_state.water_data

    # Reset day if new date has arrived
    today = str(datetime.date.today())
    if data["date"] != today:
        data["date"] = today
        data["intake"] = 0
        data["logs"] = []

    # --- Age group selector ---
    age_group = st.selectbox("Select your age group", AGE_GROUP_GOALS.keys())
    data["age_group"] = age_group
    suggested_goal = AGE_GROUP_GOALS[age_group]

    data["daily_goal"] = st.number_input(
        "Daily Goal (ml)", 
        min_value=500, 
        max_value=7000, 
        value=suggested_goal
    )

    st.write(f"Suggested: **{suggested_goal} ml**")

    st.markdown("---")

    # --- Quick Logging ---
    st.subheader("Log your water")
    if st.button(f"+{QUICK_LOG} ml"):
        data["intake"] += QUICK_LOG
        data["logs"].append(f"+{QUICK_LOG} ml @ {datetime.datetime.now().strftime('%H:%M')}")

    custom = st.number_input("Enter custom amount (ml)", min_value=50, max_value=3000, value=250)
    if st.button("Add custom amount"):
        data["intake"] += custom
        data["logs"].append(f"+{custom} ml @ {datetime.datetime.now().strftime('%H:%M')}")

    # --- Progress ---
    progress = data["intake"] / data["daily_goal"]
    st.progress(progress)

    st.metric("Today's Intake", f"{data['intake']} ml")
    st.metric("Remaining", f"{data['daily_goal'] - data['intake']} ml")

    # --- Motivational Message ---
    if progress >= 1:
        st.success("🎉 Goal completed! Amazing!")
    elif progress >= 0.5:
        st.info("👍 Good progress! Keep going!")
    elif progress > 0:
        st.warning("🙂 Nice start! Drink more!")

    st.markdown("---")

    # Logs
    st.subheader("Today's Logs")
    if data["logs"]:
        for log in reversed(data["logs"]):
            st.write(log)
    else:
        st.info("No logs yet!")

    # Reset
    if st.button("Reset Today"):
        data["intake"] = 0
        data["logs"] = []
        st.success("Reset successful")

    # Random Tip
    st.info("💡 Tip: " + random.choice(TIPS))

    # Save data to Firebase every time
    save_user_data(st.session_state.username, data)


# --------------------------
# MAIN APP FLOW
# --------------------------
def main():
    init_user_state()

    menu = st.sidebar.radio("Navigation", ["Login", "Signup", "WaterBuddy"])

    if menu == "Login":
        login_page()

    elif menu == "Signup":
        signup_page()

    elif menu == "WaterBuddy":
        if not st.session_state.logged_in:
            st.warning("Please login first!")
        else:
            waterbuddy_app()


main()
