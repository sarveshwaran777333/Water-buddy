"""
WaterBuddy - Streamlit app combining original features with a new 7-day intake history graph (Matplotlib).
FIXED: NameError in dashboard_ui by calculating core variables (intake, percent, goal) globally within the function scope.
"""

# =======================
# 1. Imports
# =======================
import streamlit as st
import requests
import json
from datetime import date, timedelta
import random
import time
import os
import matplotlib.pyplot as plt

# Lottie support (optional)
try:
    from streamlit_lottie import st_lottie
except Exception:
    st_lottie = None  # graceful fallback if streamlit-lottie not installed

# =======================
# 2. Configuration & Constants
# =======================
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
REQUEST_TIMEOUT = 8  # seconds

TIPS = [
    "Keep a filled water bottle visible on your desk.",
    "Drink a glass (250 ml) after every bathroom break.",
    "Start your day with a glass of water.",
    "Add lemon or cucumber for natural flavor.",
    "Set small hourly reminders and sip regularly.",
]

# Attempt to load Lottie progress animation (safe loading)
LOTTIE_PROGRESS = None
if st_lottie is not None:
    assets_path = os.path.join("assets", "progress_bar.json")
    if os.path.exists(assets_path):
        try:
            with open(assets_path, "r", encoding="utf-8") as f:
                LOTTIE_PROGRESS = json.load(f)
        except Exception:
            LOTTIE_PROGRESS = None
    else:
        alt = os.path.join("assets", "progress.json")
        if os.path.exists(alt):
            try:
                with open(alt, "r", encoding="utf-8") as f:
                    LOTTIE_PROGRESS = json.load(f)
            except Exception:
                LOTTIE_PROGRESS = None

# -----------------------
# Lottie helper (consolidated here)
# -----------------------
def load_lottie(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# =======================
# 3. Core Utility Functions (Firebase & User Logic)
# =======================

# Firebase REST helpers
def firebase_url(path: str) -> str:
    path = path.strip("/")
    return f"{FIREBASE_URL}/{path}.json"

def firebase_get(path: str):
    url = firebase_url(path)
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                return None
        return None
    except requests.RequestException:
        return None

def firebase_post(path: str, value):
    url = firebase_url(path)
    try:
        r = requests.post(url, data=json.dumps(value), timeout=REQUEST_TIMEOUT)
        if r.status_code in (200, 201):
            try:
                return r.json()  # expected {"name": "<key>"}
            except ValueError:
                return None
        return None
    except requests.RequestException:
        return None

def firebase_patch(path: str, value_dict: dict):
    url = firebase_url(path)
    try:
        r = requests.patch(url, data=json.dumps(value_dict), timeout=REQUEST_TIMEOUT)
        return r.status_code in (200, 201)
    except requests.RequestException:
        return False

# User & Intake helpers
def find_user_by_username(username: str):
    """Return (uid, user_obj) if found, else (None, None)."""
    data = firebase_get(USERS_NODE)
    if not isinstance(data, dict):
        return None, None
    for uid, rec in data.items():
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
    payload = {
        "username": username,
        "password": password,   # NOTE: plaintext for demo; use hashing or Firebase Auth in production
        "created_at": DATE_STR,
        "profile": {
            "age_group": "19-50",
            "user_goal_ml": AGE_GOALS_ML["19-50"]
        }
    }
    res = firebase_post(USERS_NODE, payload)
    if isinstance(res, dict) and "name" in res:
        return res["name"]
    return None

def validate_login(username: str, password: str):
    """Return (True, uid) if credentials match, else (False, None)."""
    uid, rec = find_user_by_username(username)
    if uid and isinstance(rec, dict) and rec.get("password") == password:
        return True, uid
    return False, None

def get_today_intake(uid: str):
    if not uid:
        return 0
    path = f"{USERS_NODE}/{uid}/days/{DATE_STR}/intake"
    val = firebase_get(path)
    if isinstance(val, (int, float)):
        return int(val)
    # fallback check for older root field (kept for compatibility)
    user_root = firebase_get(f"{USERS_NODE}/{uid}")
    if isinstance(user_root, dict):
        legacy = user_root.get("todays_intake_ml")
        if isinstance(legacy, (int, float)):
            return int(legacy)
    return 0

def set_today_intake(uid: str, ml_value: int):
    if not uid:
        return False
    ml = int(max(0, ml_value))
    path = f"{USERS_NODE}/{uid}/days/{DATE_STR}"
    return firebase_patch(path, {"intake": ml})

def reset_today_intake(uid: str):
    return set_today_intake(uid, 0)

def get_user_profile(uid: str):
    if not uid:
        return {"age_group": "19-50", "user_goal_ml": AGE_GOALS_ML["19-50"]}
    profile = firebase_get(f"{USERS_NODE}/{uid}/profile")
    if isinstance(profile, dict):
        # ensure int and safe default
        user_goal = profile.get("user_goal_ml", AGE_GOALS_ML["19-50"])
        try:
            user_goal = int(user_goal)
        except Exception:
            user_goal = AGE_GOALS_ML["19-50"]
        return {
            "age_group": profile.get("age_group", "19-50"),
            "user_goal_ml": user_goal
        }
    return {"age_group": "19-50", "user_goal_ml": AGE_GOALS_ML["19-50"]}

def update_user_profile(uid: str, updates: dict):
    if not uid:
        return False
    return firebase_patch(f"{USERS_NODE}/{uid}/profile", updates)

def get_username_by_uid(uid: str):
    rec = firebase_get(f"{USERS_NODE}/{uid}")
    if isinstance(rec, dict):
        return rec.get("username", "user")
    return "user"
    
def get_past_intake(uid: str, days_count: int = 7):
    """Fetches intake data for the last N days."""
    intake_data = {}
    today = date.today()
    for i in range(days_count):
        day = (today - timedelta(days=i)).isoformat()
        path = f"{USERS_NODE}/{uid}/days/{day}/intake"
        intake_value = firebase_get(path)
        # Ensure intake is a safe integer, defaulting to 0
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
    percent: 0..100
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
    sorted_days = sorted(intake_data.keys())
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
    # This function contains the extensive CSS for Light, Aqua, and Dark modes.
    # It remains unchanged from the original application logic.
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

# Login and Signup UIs
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
                    st.error("Username already taken or network error.")

    st.markdown("---")
    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# Dashboard UI (FIXED scope of core variables)
def dashboard_ui():
    uid = st.session_state.uid
    if not uid:
        st.error("Missing user id. Please login again.")
        st.session_state.logged_in = False
        st.session_state.uid = None
        st.session_state.page = "login"
        st.rerun()
        return

    profile = get_user_profile(uid)
    intake = get_today_intake(uid)
    
    # === FIX: Calculate core progress variables globally in the function scope ===
    std_goal = AGE_GOALS_ML.get(profile.get("age_group","19-50"), 2500)
    user_goal = int(profile.get("user_goal_ml", std_goal))
    remaining = max(user_goal - intake, 0)
    # This variable calculation MUST be defined before it is used for milestones/metrics.
    percent = min((intake / user_goal) * 100 if user_goal > 0 else 0, 100)
    # ===========================================================================

    left_col, right_col = st.columns([1,3])

    with left_col:
        st.subheader("Navigate")
        # Theme selector (safe index)
        theme_options = ["Light","Aqua","Dark"]
        try:
            idx = theme_options.index(st.session_state.theme)
        except Exception:
            idx = 0
            st.session_state.theme = theme_options[0]

        theme_choice = st.selectbox("Theme", theme_options, index=idx)
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            apply_theme(theme_choice)
            # update immediately visually (no rerun required)

        st.markdown("")  # spacer

        # left nav buttons
        if st.button("Home", key="nav_home"):
            st.session_state.nav = "Home"
        if st.button("Log Water", key="nav_log"):
            st.session_state.nav = "Log Water"
        if st.button("History", key="nav_history"): # NEW BUTTON
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

            # Metric now styled by apply_theme() CSS
            st.metric("Total intake (ml)", f"{intake} ml", delta=f"{remaining} ml to goal" if remaining > 0 else "Goal reached!")
            st.progress(percent / 100)

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
                    try:
                        st_lottie(LOTTIE_PROGRESS, loop=False, height=120)
                    except Exception:
                        pass
            else:
                st.write(f"Progress: {percent:.0f}%")

            # milestone messages - NOW SAFELY ACCESSING 'percent'
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
                        st.error("Failed to update. Check network/DB rules.")

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
                            st.error("Failed to update. Check network/DB rules.")

            with c3:
                if st.button("Reset today", key="reset_today"):
                    ok = reset_today_intake(uid)
                    if ok:
                        st.info("Reset successful.")
                        st.rerun()
                    else:
                        st.error("Failed to reset. Check network/DB rules.")

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
        
        # NEW PAGE: History
        elif nav == "History":
            st.header("Water Intake History")
            st.markdown("---")
            st.subheader("Last 7 Days Intake Graph")
            
            # 1. Fetch data 
            past_intake_data = get_past_intake(uid, days_count=7)
            
            # 2. Generate and display the plot
            try:
                # Pass the goal to the plotting function for reference line
                intake_plot_fig = plot_water_intake(past_intake_data, user_goal) 
                st.pyplot(intake_plot_fig) 
            except Exception as e:
                st.error(f"Could not generate graph. Error: {e}")
                st.info("Ensure you have Matplotlib installed (`pip install matplotlib`) and some data logged.")


        elif nav == "Settings":
            st.header("Settings & Profile")
            # safe index for selectbox
            age_keys = list(AGE_GOALS_ML.keys())
            try:
                idx = age_keys.index(profile.get("age_group", "19-50"))
            except Exception:
                idx = 2  # default to "19-50"
            age_choice = st.selectbox("Select age group", age_keys, index=idx)
            suggested = AGE_GOALS_ML[age_choice]
            st.write(f"Suggested: {suggested} ml")
            user_goal_val = st.number_input("Daily goal (ml)", min_value=500, max_value=10000, value=int(profile.get("user_goal_ml", suggested)), step=50)
            if st.button("Save profile", key="save_profile"):
                ok = update_user_profile(uid, {"age_group": age_choice, "user_goal_ml": int(user_goal_val)})
                if ok:
                    st.success("Profile saved.")
                else:
                    st.error("Failed to save profile. Check network/DB rules.")


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

# session state defaults
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
