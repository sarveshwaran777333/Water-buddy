"""
WaterBuddy - Streamlit app using local JSON file storage instead of Firebase.
All Firebase REST functions and helpers have been replaced by JSON read/write helpers.
The application logic remains functionally the same, but data is now stored in 'water_data.json'.
"""

# =======================
# 1. Imports
# =======================
import streamlit as st
import json
from datetime import date, timedelta
import random
import time
import os
import matplotlib.pyplot as plt
import uuid # For generating unique user IDs

# Lottie support (optional)
# FIX: The previous SyntaxError was here due to invisible characters (U+00A0).
# Ensure standard indentation is used.
try:
    from streamlit_lottie import st_lottie
except ImportError:
    st_lottie = None # graceful fallback if streamlit-lottie not installed

# =======================
# 2. Configuration & Constants
# =======================
# --- Local Data Config ---
DATA_FILE = "water_data.json"
# -----------------------------
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
    "Keep a filled water bottle visible on your desk.",
    "Drink a glass (250 ml) after every bathroom break.",
    "Start your day with a glass of water.",
    "Add lemon or cucumber for natural flavor.",
    "Set small hourly reminders and sip regularly.",
]

# Attempt to load Lottie progress animation (safe loading)
LOTTIE_PROGRESS = None
def load_lottie(path: str):
    """Safely loads a JSON Lottie file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# Load lottie file (adjust path as needed if running locally)
if st_lottie is not None:
    # Check common asset locations
    assets_path = os.path.join(os.path.dirname(__file__), "assets", "progress_bar.json")
    if os.path.exists(assets_path):
        LOTTIE_PROGRESS = load_lottie(assets_path)
    else:
        # Fallback for simpler Streamlit environments
        alt = os.path.join(os.getcwd(), "progress.json")
        if os.path.exists(alt):
            LOTTIE_PROGRESS = load_lottie(alt)

# =======================
# 3. Core Utility Functions (Local JSON Data Management)
# =======================

def load_data():
    """Loads all user data from the local JSON file."""
    if not os.path.exists(DATA_FILE):
        # Initialize file with an empty user dictionary
        initial_data = {"users": {}}
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(initial_data, f, indent=4)
        except Exception:
            return initial_data
        return initial_data
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            # Ensure the top-level structure exists
            if not isinstance(data, dict) or "users" not in data:
                 return {"users": {}}
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        # Handle corrupt or missing file
        return {"users": {}}

def save_data(data):
    """Saves all user data back to the local JSON file."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception:
        return False

# --- User & Intake helpers (adapted to use local JSON data) ---

def find_user_by_username(username: str):
    """Return (uid, user_obj) if found, else (None, None)."""
    data = load_data()
    users = data.get("users", {})
    for uid, rec in users.items():
        if isinstance(rec, dict) and rec.get("username") == username:
            return uid, rec
    return None, None

def create_user(username: str, password: str):
    """Create user - returns uid string on success, None on failure."""
    if not username or not password:
        return None
    # Ensure uniqueness
    uid, _ = find_user_by_username(username)
    if uid:
        return None
    
    new_uid = str(uuid.uuid4()) # Generate unique ID
    payload = {
        "username": username,
        "password": password,   # NOTE: plaintext for demo
        "created_at": DATE_STR,
        "profile": {
            "age_group": "19-50",
            "user_goal_ml": AGE_GOALS_ML["19-50"]
        },
        "days": {} # Initialize days node
    }
    
    data = load_data()
    data["users"][new_uid] = payload
    if save_data(data):
        return new_uid
    return None

def validate_login(username: str, password: str):
    """Return (True, uid) if credentials match, else (False, None)."""
    uid, rec = find_user_by_username(username)
    if uid and isinstance(rec, dict) and rec.get("password") == password:
        return True, uid
    return False, None

def get_today_intake(uid: str):
    """Fetches today's total intake in ml."""
    if not uid:
        return 0
    data = load_data()
    user_rec = data.get("users", {}).get(uid, {})
    
    # New data structure: days/{DATE_STR}/intake
    intake = user_rec.get("days", {}).get(DATE_STR, {}).get("intake")
    
    if isinstance(intake, (int, float)):
        return int(intake)
    
    return 0

def set_today_intake(uid: str, ml_value: int):
    """Updates today's total intake for the user."""
    if not uid:
        return False
    ml = int(max(0, ml_value))
    
    data = load_data()
    if uid not in data["users"]:
        return False
    
    user_data = data["users"][uid]
    if "days" not in user_data:
        user_data["days"] = {}
    
    # Ensure the current date node exists
    if DATE_STR not in user_data["days"]:
        user_data["days"][DATE_STR] = {}
        
    # Update the intake value
    user_data["days"][DATE_STR]["intake"] = ml
    
    return save_data(data)

def reset_today_intake(uid: str):
    return set_today_intake(uid, 0)

def get_user_profile(uid: str):
    default_profile = {"age_group": "19-50", "user_goal_ml": AGE_GOALS_ML["19-50"]}
    if not uid:
        return default_profile
    
    data = load_data()
    user_rec = data.get("users", {}).get(uid, {})
    profile = user_rec.get("profile")

    if isinstance(profile, dict):
        # Safely determine the goal, defaulting if corrupted
        user_goal = profile.get("user_goal_ml")
        try:
            user_goal = int(user_goal)
        except Exception:
            user_goal = default_profile["user_goal_ml"]
        
        return {
            "age_group": profile.get("age_group", default_profile["age_group"]),
            "user_goal_ml": user_goal
        }
    return default_profile

def update_user_profile(uid: str, updates: dict):
    """Updates the user's profile settings."""
    if not uid:
        return False
    
    data = load_data()
    if uid not in data["users"]:
        return False
    
    # Initialize profile if it doesn't exist
    user_profile = data["users"][uid].get("profile", {})
    user_profile.update(updates)
    data["users"][uid]["profile"] = user_profile
    
    return save_data(data)

def get_username_by_uid(uid: str):
    """Fetches the username for display."""
    data = load_data()
    rec = data.get("users", {}).get(uid)
    if isinstance(rec, dict):
        return rec.get("username", "user")
    return "user"
    
def get_past_intake(uid: str, days_count: int = 7):
    """Fetches intake data for the last N days."""
    if not uid:
        return {}
    
    data = load_data()
    user_rec = data.get("users", {}).get(uid, {})
    days_data = user_rec.get("days", {})
    
    intake_data = {}
    today = date.today()
    
    for i in range(days_count):
        day = (today - timedelta(days=i)).isoformat()
        # Access data from the local JSON structure: days/{date}/intake
        intake_value = days_data.get(day, {}).get("intake")
        
        try:
            intake_data[day] = int(intake_value) if intake_value is not None else 0
        except:
            intake_data[day] = 0
    return intake_data

# =======================
# 4. UI Helpers (SVG, Matplotlib Plotting, Theme CSS)
# =======================

def generate_bottle_svg(percent: float, width:int=140, height:int=360) -> str:
    """
    Simple bottle SVG with dynamic fill height.
    """
    pct = max(0.0, min(100.0, float(percent)))
    inner_w = width - 36
    inner_h = height - 80
    fill_h = (pct / 100.0) * inner_h
    empty_h = inner_h - fill_h

    # Coordinates are chosen to keep visual proportions consistent.
    svg = f"""
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
    <rect x="12" y="12" rx="20" ry="20" width="{width-24}" height="{height-24}" fill="none" stroke="#5dade2" stroke-width="3"/>
    <rect x="18" y="18" width="{inner_w}" height="{inner_h}" rx="12" ry="12" fill="#f3fbff"/>
    <rect x="18" y="{18 + empty_h}" width="{inner_w}" height="{fill_h}" rx="12" ry="12" fill="#67b3df"/>
    <rect x="{(width/2)-18}" y="0" width="36" height="18" rx="4" ry="4" fill="#3498db"/>
    <text x="{width/2}" y="{height-8}" font-size="14" text-anchor="middle" fill="#023047" font-family="Arial">{pct:.0f}%</text>
</svg>
"""
    return svg

def plot_water_intake(intake_data, goal):
    """Generate a Matplotlib line chart showing daily water intake."""
    
    # Sort data by date (key) to ensure the chart is in chronological order
    sorted_days = sorted(intake_data.keys(), reverse=True)
    # Reverse the list so the chart goes from older dates to today
    sorted_days.reverse()
    
    # Extract values in the sorted order
    intakes = [intake_data[day] for day in sorted_days]
    
    # Format labels to be shorter (e.g., '12-05')
    labels = [d.split('-')[1] + '-' + d.split('-')[2] for d in sorted_days]
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(labels, intakes, marker='o', color='#3498db', label="Water Intake (ml)", linewidth=2)
    
    # Add goal line 
    ax.axhline(y=goal, color='#2ecc71', linestyle='--', label=f'Goal ({goal} ml)')

    # Customize the plot
    ax.set_title("Daily Water Intake Over the Last 7 Days", fontsize=16)
    ax.set_xlabel("Date (MM-DD)", fontsize=12)
    ax.set_ylabel("Water Intake (ml)", fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend()
    plt.tight_layout()

    return fig

# Theme CSS
def apply_theme(theme_name: str):
    """Applies custom CSS for themeing the Streamlit UI."""
    if theme_name == "Light":
        st.markdown("""
        <style>
        .stApp { background-color: #ffffff !important; color: #000000 !important; }
        h1, h2, h3, h4, h5, h6, p, label, span { color: #000000 !important; }
        .stButton>button { background-color: #e6e6e6 !important; color: #000000 !important; border-radius: 8px !important; border: 1px solid #cccccc !important; }
        .stButton>button:hover { background-color: #d9d9d9 !important; }
        .stTextInput>div>div>input { background-color: #fafafa !important; color: #000000 !important; border-radius: 6px !important; }
        .stSlider>div>div>div { background-color: #007acc !important; }
        div[data-testid="metric-container"] { background-color: #f7f7f7 !important; border-radius: 12px !important; padding: 12px !important; border: 1px solid #e1e1e1 !important; }
        div[data-testid="metric-container"] label { color: #000000 !important; font-weight: 600 !important; }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 700 !important; font-size: 1.5rem !important; }
        div[data-testid="metric-container"] [data-testid="metric-delta"] { color: #006600 !important; font-weight: 600 !important; }
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] > span,
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] span { color: inherit !important; }
        </style>
        """, unsafe_allow_html=True)

    elif theme_name == "Aqua":
        st.markdown("""
        <style>
        .stApp { background-color: #e8fbff !important; color: #004455 !important; }
        h1, h2, h3, h4, h5, h6, p, label, span { color: #004455 !important; }
        .stButton>button { background-color: #c6f3ff !important; color: #004455 !important; border-radius: 8px !important; border: 1px solid #99e6ff !important; }
        .stButton>button:hover { background-color: #b3edff !important; }
        .stTextInput>div>div>input { background-color: #ffffff !important; color: #003344 !important; border-radius: 6px !important; }
        .stSlider>div>div>div { background-color: #00aacc !important; }
        div[data-testid="metric-container"] { background-color: #d9f7ff !important; border-radius: 12px !important; padding: 12px !important; border: 1px solid #bdefff !important; }
        div[data-testid="metric-container"] label { color: #005577 !important; font-weight: 600 !important; }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #005577 !important; font-weight: 700 !important; font-size: 1.5rem !important; }
        div[data-testid="metric-container"] [data-testid="metric-delta"] { color: #0077b6 !important; font-weight: 600 !important; }
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] > span,
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] span { color: inherit !important; }
        </style>
        """, unsafe_allow_html=True)

    else: # Dark Mode
        st.markdown("""
        <style>
        .stApp { background-color: #0f1720 !important; color: #e6eef6 !important; }
        h1, h2, h3, h4, h5, h6, p, label, span { color: #e6eef6 !important; }
        .stButton>button { background-color: #1e2933 !important; color: #e6eef6 !important; border-radius: 8px !important; border: 1px solid #324151 !important; }
        .stButton>button:hover { background-color: #253241 !important; }
        .stTextInput>div>div>input { background-color: #1e2933 !important; color: #e6eef6 !important; border-radius: 6px !important; }
        .stSlider>div>div>div { background-color: #3b82f6 !important; }
        div[data-testid="metric-container"] { background-color: #1a2634 !important; border-radius: 12px !important; padding: 12px !important; border: 1px solid #334155 !important; }
        div[data-testid="metric-container"] label { color: #e6eef6 !important; font-weight: 600 !important; }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e6eef6 !important; font-weight: 700 !important; font-size: 1.5rem !important; }
        div[data-testid="metric-container"] [data-testid="metric-delta"] { color: #4caf50 !important; font-weight: 600 !important; }
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] > span,
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] span { color: inherit !important; }
        </style>
        """, unsafe_allow_html=True)


# =======================
# 5. Streamlit App Layout Functions
# =======================

def login_ui():
    st.header("Login (username + password)")
    col1, col2 = st.columns([3,1])
    with col1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
    with col2:
        if st.button("Login"):
            if not username or not password:
                st.warning("Enter both username and password.")
            else:
                ok, uid = validate_login(username.strip(), password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.uid = uid
                    st.session_state.page = "dashboard"
                    st.success("Login successful.")
                    time.sleep(0.25)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    st.markdown("---")
    if st.button("Create new account"):
        st.session_state.page = "signup"
        st.rerun()

def signup_ui():
    st.header("Sign Up (username + password)")
    col1, col2 = st.columns([3,1])
    with col1:
        username = st.text_input("Choose a username", key="signup_username")
        password = st.text_input("Choose a password", type="password", key="signup_password")
    with col2:
        if st.button("Register"):
            if not username or not password:
                st.warning("Enter both username and password.")
            else:
                uid = create_user(username.strip(), password)
                if uid:
                    st.success("Account created. Please log in.")
                    st.session_state.page = "login"
                    time.sleep(0.25)
                    st.rerun()
                else:
                    st.error("Username already taken or failed to save data.")

    st.markdown("---")
    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

def dashboard_ui():
    uid = st.session_state.uid
    if not uid:
        # Should be caught by main logic, but safety check
        st.error("Missing user id. Please login again.")
        st.session_state.logged_in = False
        st.session_state.uid = None
        st.session_state.page = "login"
        st.rerun()
        return

    profile = get_user_profile(uid)
    intake = get_today_intake(uid)
    
    # === Calculate core progress variables ===
    std_goal = AGE_GOALS_ML.get(profile.get("age_group","19-50"), 2500)
    user_goal = int(profile.get("user_goal_ml", std_goal))
    remaining = max(user_goal - intake, 0)
    percent = min((intake / user_goal) * 100 if user_goal > 0 else 0, 100)
    # =========================================

    left_col, right_col = st.columns([1,3])

    with left_col:
        st.subheader("Navigate")
        
        # Theme selector 
        theme_options = ["Light","Aqua","Dark"]
        try:
            idx = theme_options.index(st.session_state.theme)
        except Exception:
            idx = 0
            st.session_state.theme = theme_options[0]

        theme_choice = st.selectbox("Theme", theme_options, index=idx)
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            # Re-apply theme without rerunning app logic (visual only)
            apply_theme(theme_choice) 

        st.markdown("") # spacer

        # left nav buttons
        if st.button("Home", key="nav_home"):
            st.session_state.nav = "Home"
        if st.button("Log Water", key="nav_log"):
            st.session_state.nav = "Log Water"
        if st.button("History", key="nav_history"):
            st.session_state.nav = "History"
        if st.button("Settings", key="nav_settings"):
            st.session_state.nav = "Settings"
        if st.button("Logout", key="nav_logout"):
            st.session_state.logged_in = False
            st.session_state.uid = None
            st.session_state.page = "login"
            st.session_state.nav = "Home"
            st.rerun()

        st.markdown("---")
        st.write("Tip of the day")
        st.info(st.session_state.tip)
        if st.button("New tip", key="new_tip"):
            st.session_state.tip = random.choice(TIPS)

    # ensure theme for right pane
    apply_theme(st.session_state.theme)

    with right_col:
        nav = st.session_state.nav

        if nav == "Home":
            st.header("Today's Summary")
            st.write(f"User: **{get_username_by_uid(uid)}**")
            st.write(f"Date: {DATE_STR}")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Standard target")
                st.write(f"**{std_goal} ml**")
            with col2:
                st.subheader("Your target")
                st.write(f"**{user_goal} ml**")

            st.metric("Total intake (ml)", f"{intake} ml", delta=f"{remaining} ml to goal" if remaining > 0 else "Goal reached!")
            st.progress(percent / 100)

            # Display the water bottle SVG 
            svg = generate_bottle_svg(percent)
            st.components.v1.html(svg, height=360, scrolling=False)

            # Lottie progress bar (optional)
            if st_lottie is not None and LOTTIE_PROGRESS is not None:
                try:
                    total_frames = 150
                    end_frame = int(total_frames * (percent / 100.0))
                    if end_frame < 1:
                        end_frame = 1
                    st_lottie(LOTTIE_PROGRESS, loop=False, start_frame=0, end_frame=end_frame, height=120)
                except Exception:
                    pass
            else:
                st.write(f"Progress: {percent:.0f}%")

            # milestone messages
            if percent >= 100:
                st.success("🎉 Amazing — you reached your daily goal!")
            elif percent >= 75:
                st.info("Great — 75% reached!")
            elif percent >= 50:
                st.info("Nice — 50% reached!")
            elif percent >= 25:
                st.info("Good start — 25% reached!")

        elif nav == "Log Water":
            st.header("Log Water Intake")
            st.write(f"Today's intake: **{intake} ml**")

            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                if st.button(f"+{DEFAULT_QUICK_LOG_ML} ml", key="quick_log"):
                    new_val = intake + DEFAULT_QUICK_LOG_ML
                    ok = set_today_intake(uid, new_val)
                    if ok:
                        st.success(f"Added {DEFAULT_QUICK_LOG_ML} ml.")
                        st.rerun()
                    else:
                        st.error("Failed to update.")

            with c2:
                custom = st.number_input("Custom amount (ml)", min_value=0, step=50, key="custom_input")
                if st.button("Add custom", key="add_custom"):
                    if custom <= 0:
                        st.warning("Enter amount > 0")
                    else:
                        new_val = intake + int(custom)
                        ok = set_today_intake(uid, new_val)
                        if ok:
                            st.success(f"Added {int(custom)} ml.")
                            st.rerun()
                        else:
                            st.error("Failed to update.")

            with c3:
                if st.button("Reset today", key="reset_today"):
                    ok = reset_today_intake(uid)
                    if ok:
                        st.info("Reset successful.")
                        st.rerun()
                    else:
                        st.error("Failed to reset.")

            st.markdown("---")
            st.subheader("Unit converter")
            cc1, cc2 = st.columns(2)
            with cc1:
                cups = st.number_input("Cups", min_value=0.0, step=0.5, key="conv_cups")
                if st.button("Convert cups → ml", key="conv_to_ml"):
                    ml_conv = round(cups * CUPS_TO_ML, 1)
                    st.success(f"{cups} cups = {ml_conv} ml")
            with cc2:
                ml_in = st.number_input("Milliliters", min_value=0.0, step=50.0, key="conv_ml")
                if st.button("Convert ml → cups", key="conv_to_cups"):
                    cups_conv = round(ml_in / CUPS_TO_ML, 2)
                    st.success(f"{ml_in} ml = {cups_conv} cups")
            
        elif nav == "History":
            st.header("Water Intake History")
            st.markdown("---")
            st.subheader("Last 7 Days Intake Graph")
            
            # 1. Fetch data 
            past_intake_data = get_past_intake(uid, days_count=7)
            
            # 2. Generate and display the plot 

[Image of a line graph showing daily water intake over 7 days]

            try:
                # Pass the goal to the plotting function for reference line
                intake_plot_fig = plot_water_intake(past_intake_data, user_goal) 
                st.pyplot(intake_plot_fig) 
            except Exception as e:
                st.error(f"Could not generate graph. Ensure you have Matplotlib installed (`pip install matplotlib`) and some data logged.")


        elif nav == "Settings":
            st.header("Settings & Profile")
            # safe index for selectbox
            age_keys = list(AGE_GOALS_ML.keys())
            try:
                idx = age_keys.index(profile.get("age_group", "19-50"))
            except Exception:
                idx = 2 # default to "19-50"
            age_choice = st.selectbox("Select age group", age_keys, index=idx)
            suggested = AGE_GOALS_ML[age_choice]
            st.write(f"Suggested intake for this group: {suggested} ml")
            user_goal_val = st.number_input("Daily goal (ml)", min_value=500, max_value=10000, value=int(profile.get("user_goal_ml", suggested)), step=50)
            if st.button("Save profile", key="save_profile"):
                ok = update_user_profile(uid, {"age_group": age_choice, "user_goal_ml": int(user_goal_val)})
                if ok:
                    st.success("Profile saved. Goal updated.")
                    st.rerun()
                else:
                    st.error("Failed to save profile.")


# =======================
# 6. Main App Routing
# =======================
st.set_page_config(page_title="WaterBuddy", layout="wide")

# ensure theme applied early using session_state default (set below)
if "theme" not in st.session_state:
    st.session_state.theme = "Light"
# immediately apply so initial render looks correct
apply_theme(st.session_state.theme)

st.title("WaterBuddy — Hydration Tracker")

# Initialize session state defaults
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "uid" not in st.session_state:
    st.session_state.uid = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "nav" not in st.session_state:
    st.session_state.nav = "Home"
if "tip" not in st.session_state:
    st.session_state.tip = random.choice(TIPS)

# App routing
if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_ui()
    else:
        login_ui()
else:
    dashboard_ui()
