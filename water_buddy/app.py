import streamlit as st
import random

st.set_page_config(page_title="WaterBuddy", page_icon="💧")

# -------------------------------------------------------
# INITIALIZE SESSION STATE
# -------------------------------------------------------
if "users" not in st.session_state:
    st.session_state.users = {}     # {username: password}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if "intake" not in st.session_state:
    st.session_state.intake = 0

if "daily_goal" not in st.session_state:
    st.session_state.daily_goal = None


# -------------------------------------------------------
# SIGNUP PAGE
# -------------------------------------------------------
def signup_page():
    st.title("WaterBuddy – Create an Account")

    new_user = st.text_input("Choose a Username")
    new_pass = st.text_input("Create Password", type="password")

    if st.button("Sign Up"):
        if new_user == "" or new_pass == "":
            st.warning("Username and password cannot be empty.")
        elif new_user in st.session_state.users:
            st.error("This username is already taken.")
        else:
            st.session_state.users[new_user] = new_pass
            st.success("Account created successfully. Please log in.")


    if st.button("Already have an account? Login"):
        st.session_state.page = "login"


# -------------------------------------------------------
# LOGIN PAGE
# -------------------------------------------------------
def login_page():
    st.title("WaterBuddy – Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user in st.session_state.users and st.session_state.users[user] == pwd:
            st.session_state.logged_in = True
            st.session_state.username = user
            st.success("Login successful")
        else:
            st.error("Invalid login credentials.")

    if st.button("Create New Account"):
        st.session_state.page = "signup"


# -------------------------------------------------------
# MAIN WATERBUDDY APP
# -------------------------------------------------------
def waterbuddy_home():

    st.title("WaterBuddy – Your Personal Hydration Tracker")

    # -------------------------------
    # AGE SELECTION AND GOAL SETTING
    # -------------------------------
    st.subheader("Step 1: Choose Age Group")

    age_group = st.selectbox(
        "Select your age range:",
        ["6–12", "13–18", "19–50", "65+"],
    )

    # Age-based standard goals
    standard_goals = {
        "6–12": 1600,
        "13–18": 1800,
        "19–50": 2500,
        "65+": 2000,
    }

    default_goal = standard_goals[age_group]

    st.write(f"Standard suggested goal: {default_goal} ml")

    st.subheader("Step 2: Adjust Daily Goal (Optional)")
    st.session_state.daily_goal = st.number_input(
        "Set your personal daily goal (ml):",
        min_value=500,
        max_value=4000,
        value=default_goal,
        step=50
    )

    # -------------------------------
    # LOG WATER INTAKE
    # -------------------------------
    st.subheader("Step 3: Log Your Intake")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("+250 ml"):
            st.session_state.intake += 250

    with col2:
        manual = st.number_input("Or enter a custom amount (ml):", 0, 2000, 0, 50)
        if st.button("Add Intake"):
            st.session_state.intake += manual

    # -------------------------------
    # RESET BUTTON
    # -------------------------------
    if st.button("Reset Today"):
        st.session_state.intake = 0

    # -------------------------------
    # CALCULATIONS
    # -------------------------------
    intake = st.session_state.intake
    goal = st.session_state.daily_goal

    remaining = goal - intake if goal > intake else 0
    percentage = min(100, int((intake / goal) * 100))

    st.write(f"Total Water Consumed: {intake} ml")
    st.write(f"Remaining to reach goal: {remaining} ml")

    # PROGRESS BAR
    st.progress(percentage / 100)

    # -------------------------------
    # MOTIVATIONAL MESSAGES
    # -------------------------------
    if percentage < 25:
        st.info("Good start! Keep going.")
    elif percentage < 50:
        st.info("Nice progress. Halfway coming soon.")
    elif percentage < 75:
        st.success("Great! You crossed 50%.")
    elif percentage < 100:
        st.success("Almost there! Stay hydrated.")
    else:
        st.success("Congratulations! You reached your daily target.")

    # -------------------------------
    # RANDOM DAILY TIPS
    # -------------------------------
    tips = [
        "Drinking water boosts your concentration.",
        "Water helps digestion and metabolism.",
        "Start your day with a glass of water.",
        "Keep a water bottle near you while working.",
        "Staying hydrated improves mood and energy.",
    ]

    st.subheader("Hydration Tip of the Day")
    st.write(random.choice(tips))

    # -------------------------------
    # LOGOUT BUTTON
    # -------------------------------
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None


# -------------------------------------------------------
# PAGE NAVIGATION HANDLING
# -------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "login"

if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_page()
    else:
        login_page()
else:
    waterbuddy_home()
