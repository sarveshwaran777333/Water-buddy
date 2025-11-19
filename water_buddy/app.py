import streamlit as st
import requests
import datetime
import hashlib

# =========================
# CONFIG
# =========================
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"


def apply_theme():
    theme = st.session_state.get("theme", "Light")

    if theme == "Light":
        st.markdown("""
            <style>
            body { background-color: #FFFFFF; color: #000000; }
            .stButton>button { background-color: #ADD8E6; color: black; }
            </style>
        """, unsafe_allow_html=True)

    elif theme == "Dark":
        st.markdown("""
            <style>
            body { background-color: #1E1E1E; color: #FFFFFF; }
            .stButton>button { background-color: #444444; color: white; }
            </style>
        """, unsafe_allow_html=True)

    elif theme == "Aqua":
        st.markdown("""
            <style>
            body { background-color: #CFF5FF; color: #004488; }
            .stButton>button { background-color: #7F5FFF; color: white; }
            </style>
        """, unsafe_allow_html=True)


# =========================
# AGE GROUPS -> GOAL (mL)
# =========================
AGE_GROUP_GOALS_ML = {
    "6-12": 1600,
    "13-18": 1800,
    "19-50": 2500,
    "65+": 2000
}


# =========================
# AGE GROUP DETECTOR
# =========================
def get_age_group(age):
    if age <= 12:
        return "6-12"
    elif age <= 18:
        return "13-18"
    elif age <= 50:
        return "19-50"
    else:
        return "65+"


# =========================
# PASSWORD HASHING
# =========================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# =========================
# FIREBASE HELPERS
# =========================
def firebase_get(path):
    url = f"{FIREBASE_URL}/{path}.json"
    return requests.get(url).json()


def firebase_put(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    return requests.put(url, json=data).json()


# =========================
# SIGNUP PAGE
# =========================
def signup_page():
    apply_theme()
    st.title("Create Account")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        if not username or not password:
            st.error("Please enter both username & password")
            return

        users = firebase_get("users") or {}

        if username in users:
            st.error("Username already exists!")
            return

        users[username] = {
            "password": hash_password(password),
            "goal": 2000,
            "age": 18
        }

        firebase_put("users", users)
        st.success("Account created! Please login now.")
        st.session_state.page = "login"


# =========================
# LOGIN PAGE
# =========================
def login_page():
    apply_theme()
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users = firebase_get("users") or {}

        if username not in users:
            st.error("User does not exist!")
            return

        if users[username]["password"] != hash_password(password):
            st.error("Incorrect password!")
            return

        st.success("Login successful!")

        st.session_state.logged_in = True
        st.session_state.username = username

        user_data = users[username]
        st.session_state.age = user_data.get("age", 18)
        st.session_state.age_group = get_age_group(st.session_state.age)
        st.session_state.daily_goal = user_data.get("goal", 2000)
        st.session_state.intake = 0

        # Theme load
        st.session_state.theme = user_data.get("theme", "Light")

        # GO TO HOME PAGE AFTER LOGIN
        st.session_state.page = "home"

    st.write("Don't have an account?")
    if st.button("Create New Account"):
        st.session_state.page = "signup"


# =========================
# SETTINGS PAGE
# =========================
def settings_page():
    apply_theme()
    st.title("⚙️ Settings")

    st.subheader("👤 Age Settings")

    # ---------------------------------------
    # AGE DROPDOWN
    # ---------------------------------------
    age_ranges = {
        "Age between 6-12": "6-12",
        "Age between 13-18": "13-18",
        "Age between 19-50": "19-50",
        "Age above 65+": "65+"
    }

    # Pre-select current value if exists
    current_age_label = next(
        (label for label, val in age_ranges.items() if val == st.session_state.get("age_group")),
        "Age between 6-12"
    )

    selected_label = st.selectbox(
        "Select your age range",
        list(age_ranges.keys()),
        index=list(age_ranges.keys()).index(current_age_label)
    )

    selected_age_group = age_ranges[selected_label]
    auto_goal = AGE_GROUP_GOALS_ML.get(selected_age_group, 2000)

    st.write(f"**Selected Age Group:** {selected_age_group}")
    st.write(f"**Recommended Daily Goal:** {auto_goal} ml")

    # ---------------------------------------
    # MANUAL GOAL OVERRIDE
    # ---------------------------------------
    user_goal = st.number_input(
        "Set your custom daily water goal (ml):",
        min_value=500, max_value=5000,
        value=st.session_state.get("daily_goal", auto_goal),
        step=100
    )

    st.subheader("🎨 Theme")

    theme_options = ["Light", "Dark", "Aqua"]
    current_theme = st.session_state.get("theme", "Light")

    theme = st.selectbox(
        "Choose Theme",
        theme_options,
        index=theme_options.index(current_theme)
    )

    # ---------------------------------------
    # SAVE BUTTON
    # ---------------------------------------
    if st.button("💾 Save Settings"):
        st.session_state.age_group = selected_age_group
        st.session_state.daily_goal = user_goal
        st.session_state.theme = theme

        # Apply theme instantly
        apply_theme()

        # SAVE TO FIREBASE
        users = firebase_get("users") or {}
        users[st.session_state.username]["goal"] = user_goal
        users[st.session_state.username]["age_group"] = selected_age_group
        firebase_put("users", users)

        st.success("Settings saved successfully!")

    # ---------------------------------------
    # LOGOUT BUTTON
    # ---------------------------------------
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.page = "login"
        return

    # ---------------------------------------
    # GO HOME BUTTON
    # ---------------------------------------
    if st.button("Go to Home Page"):
        st.session_state.page = "home"
        return


# =========================
# HOME PAGE
# =========================
def home_page():
    apply_theme()
    st.title("🏠 Home")

    st.write(f"**Daily Goal:** {st.session_state.daily_goal} ml")

    # Log water
    if st.button("+250 ml"):
        st.session_state.intake += 250

    custom = st.number_input("Add custom amount (ml)", min_value=0)
    if st.button("Add"):
        st.session_state.intake += custom

    # Reset
    if st.button("Reset"):
        st.session_state.intake = 0

    st.write(f"**Total Intake:** {st.session_state.intake} ml")

    # Progress bar
    progress = min(st.session_state.intake / st.session_state.daily_goal, 1.0)
    st.progress(progress)

    if progress >= 1:
        st.success("🎉 You reached your goal!")
    elif progress >= 0.5:
        st.info("👍 Halfway there!")
# --- Settings Button ---
    if st.button("⚙️ Settings"):
        st.session_state.page = "settings"
        return

# =========================
# MAIN
# =========================
def main():
    st.set_page_config(page_title="WaterBuddy", layout="centered")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "page" not in st.session_state:
        st.session_state.page = "login"

    # NO SIDEBAR BUTTONS (REMOVED)
    st.sidebar.empty()

    if not st.session_state.logged_in:
        if st.session_state.page == "signup":
            signup_page()
        else:
            login_page()
    else:
        if st.session_state.page == "settings":
            settings_page()
        elif st.session_state.page == "home":
            home_page()


main()



