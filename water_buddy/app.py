# app.py
"""
WaterBuddy (single-file Streamlit app)
- Username + password signup/login (no email)
- Stores user data in Firebase Realtime Database (REST API)
- Left navigation pane, right content pane
- Age-based suggested goal + manual override
- +250 ml quick log, custom log, reset today
- Daily intake stored as: users/<uid>/days/<YYYY-MM-DD>/intake
- Progress bar + SVG bottle, milestone messages, tips, unit converter
"""

import streamlit as st
import requests
import json
from datetime import date
import random
import math

# ---------------------------
# CONFIG
# ---------------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"
USERS_NODE = "users"  # top-level node for users in the DB
DATE_STR = date.today().isoformat()

# Age-based standard goals (ml)
AGE_GOALS_ML = {
    "6-12": 1600,
    "13-18": 2000,
    "19-50": 2500,
    "65+": 2000,
}

DEFAULT_QUICK_LOG_ML = 250
CUPS_TO_ML = 236.588

TIPS = [
    "Keep a filled bottle on your desk — visible cues help.",
    "Drink a glass (250 ml) after every bathroom break.",
    "Start your day with a glass of water.",
    "Add a slice of lemon or cucumber for flavor.",
    "Set a small goal: 1 glass every hour.",
    "Drink water before meals — it helps digestion.",
]

# ---------------------------
# Helper: Firebase REST I/O
# ---------------------------
def firebase_read(path):
    """Read JSON data from FIREBASE_URL/<path>.json"""
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        st.error("Network error when reading from Firebase.")
        return None

def firebase_put(path, value):
    """Write/replace JSON at FIREBASE_URL/<path>.json"""
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        r = requests.put(url, data=json.dumps(value), timeout=8)
        return r.status_code == 200
    except Exception as e:
        st.error("Network error when writing to Firebase.")
        return False

def firebase_patch(path, value_dict):
    """Patch JSON fields at FIREBASE_URL/<path>.json"""
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        r = requests.patch(url, data=json.dumps(value_dict), timeout=8)
        return r.status_code == 200
    except Exception as e:
        st.error("Network error when patching Firebase.")
        return False

def firebase_post(path, value):
    """Push a new node under path (returns created object or None)"""
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        r = requests.post(url, data=json.dumps(value), timeout=8)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        st.error("Network error when posting to Firebase.")
        return None

# ---------------------------
# User management helpers
# ---------------------------
def find_user_by_username(username):
    """Return (uid, user_obj) if found, else (None, None)"""
    all_users = firebase_read(USERS_NODE)
    if not all_users:
        return None, None
    for uid, obj in all_users.items():
        if obj.get("username") == username:
            return uid, obj
    return None, None

def create_user(username, password):
    """Create user if username not taken. Returns uid on success, None otherwise."""
    uid, _ = find_user_by_username(username)
    if uid:
        return None  # already exists
    payload = {
        "username": username,
        "password": password,  # NOTE: plaintext for demo only
        "created_at": DATE_STR,
        "todays_intake_ml": 0,
        "profile": {
            "age_group": "19-50",
            "user_goal_ml": AGE_GOALS_ML["19-50"]
        }
    }
    res = firebase_post(USERS_NODE, payload)
    # Firebase POST returns a dict like {"name": "-Mabcd..."} where the value is the new key
    if res and "name" in res:
        return res["name"]
    return None

def validate_login(username, password):
    """Return (True, uid) if login ok; else (False, None)"""
    uid, user_obj = find_user_by_username(username)
    if uid and user_obj.get("password") == password:
        return True, uid
    return False, None

# ---------------------------
# Data helpers (per-day)
# ---------------------------
def get_today_intake(uid):
    path = f"{USERS_NODE}/{uid}/days/{DATE_STR}/intake"
    val = firebase_read(path)
    return val if isinstance(val, (int, float)) else 0

def set_today_intake(uid, ml_value):
    path = f"{USERS_NODE}/{uid}/days/{DATE_STR}"
    data = {"intake": int(ml_value)}
    return firebase_patch(path, data)

def reset_today_intake(uid):
    return set_today_intake(uid, 0)

def get_user_profile(uid):
    path = f"{USERS_NODE}/{uid}/profile"
    profile = firebase_read(path)
    # defaults if missing
    if not profile:
        return {"age_group": "19-50", "user_goal_ml": AGE_GOALS_ML["19-50"]}
    # ensure keys exist
    return {
        "age_group": profile.get("age_group", "19-50"),
        "user_goal_ml": profile.get("user_goal_ml", AGE_GOALS_ML.get(profile.get("age_group","19-50"), 2500))
    }

def update_user_profile(uid, profile_dict):
    path = f"{USERS_NODE}/{uid}/profile"
    return firebase_patch(path, profile_dict)

# ---------------------------
# UI utility: SVG water bottle
# ---------------------------
def generate_bottle_svg(percent: float, width:int=140, height:int=360) -> str:
    percent = max(0.0, min(100.0, float(percent)))
    inner_w = width - 36
    inner_h = height - 80
    fill_h = (percent / 100.0) * inner_h
    empty_h = inner_h - fill_h
    svg = f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <rect x="12" y="12" rx="20" ry="20" width="{width-24}" height="{height-24}" fill="none" stroke="#216ba5" stroke-width="4"/>
      <rect x="24" y="36" width="{inner_w}" height="{inner_h}" rx="12" ry="12" fill="#e9f6fb"/>
      <rect x="24" y="{36 + empty_h}" width="{inner_w}" height="{fill_h}" rx="12" ry="12" fill="#2ca6e0"/>
      <text x="{width/2}" y="{height-10}" font-size="14" text-anchor="middle" fill="#083d57">{percent:.0f}%</text>
    </svg>
    """
    return svg

# ---------------------------
# Streamlit app
# ---------------------------
st.set_page_config(page_title="WaterBuddy", page_icon="💧", layout="wide")
st.title("WaterBuddy — Hydration Tracker")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "uid" not in st.session_state:
    st.session_state.uid = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "tip" not in st.session_state:
    st.session_state.tip = random.choice(TIPS)

# ---------------------------
# Login / Signup UIs
# ---------------------------
def login_ui():
    st.header("Login (username + password)")
    col1, col2 = st.columns([2,1])
    with col1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
    with col2:
        if st.button("Login"):
            ok, uid = validate_login(username.strip(), password)
            if ok:
                st.session_state.logged_in = True
                st.session_state.uid = uid
                st.success("Login successful.")
                st.session_state.page = "dashboard"
                st.experimental_rerun()
            else:
                st.error("Invalid username or password.")
    st.write("---")
    if st.button("Create new account"):
        st.session_state.page = "signup"
        st.experimental_rerun()

def signup_ui():
    st.header("Sign Up (choose username + password)")
    col1, col2 = st.columns([2,1])
    with col1:
        username = st.text_input("Choose a username", key="signup_username")
        password = st.text_input("Choose a password", type="password", key="signup_password")
    with col2:
        if st.button("Register"):
            username_val = username.strip()
            if not username_val or not password:
                st.error("Enter a non-empty username and password.")
            else:
                uid = create_user(username_val, password)
                if uid:
                    st.success("Account created. You may now log in.")
                    st.session_state.page = "login"
                else:
                    st.error("Username already taken. Choose another.")
    st.write("---")
    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.experimental_rerun()

# ---------------------------
# Dashboard: Left (nav) and Right (content)
# ---------------------------
def dashboard_ui():
    # get latest profile and today's intake
    profile = get_user_profile(st.session_state.uid)
    todays = get_today_intake(st.session_state.uid)

    left_col, right_col = st.columns([1, 3])

    with left_col:
        st.subheader("Navigation")
        nav = st.radio("Menu", ["Home", "Log Water", "Settings", "Logout"], index=0)

        st.markdown("---")
        st.write("Tip of the day:")
        st.info(st.session_state.tip)
        if st.button("New tip"):
            st.session_state.tip = random.choice(TIPS)
            st.experimental_rerun()

    with right_col:
        if nav == "Home":
            st.header("Today's Summary")
            st.write(f"Username: **{get_username_by_uid(st.session_state.uid)}**")
            st.write(f"Date: {DATE_STR}")

            # Goals
            std_goal = AGE_GOALS_ML.get(profile.get("age_group", "19-50"), 2500)
            user_goal = int(profile.get("user_goal_ml", std_goal))

            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Standard target")
                st.write(f"**{std_goal} ml**")
            with col_b:
                st.subheader("Your target")
                st.write(f"**{user_goal} ml**")

            # Intake and progress
            intake = todays
            remaining = max(user_goal - intake, 0)
            percent = min((intake / user_goal) * 100 if user_goal>0 else 0, 100)

            st.metric("Total intake (ml)", f"{intake} ml", delta=f"{remaining} ml to goal" if remaining>0 else "Goal reached!")

            st.progress(percent / 100)
            # SVG bottle centered
            svg = generate_bottle_svg(percent)
            st.components.v1.html(svg, height=380)

            # Milestones messages
            if percent >= 100:
                st.success("🎉 Amazing — you reached 100% of your goal!")
            elif percent >= 75:
                st.info("Great — you've reached 75%!")
            elif percent >= 50:
                st.info("Nice — 50% reached!")
            elif percent >= 25:
                st.info("Good start — 25% reached!")

        elif nav == "Log Water":
            st.header("Log Water Intake")

            st.write(f"Today's intake: **{todays} ml**")
            c1, c2, c3 = st.columns([1,1,1])

            with c1:
                if st.button(f"+{DEFAULT_QUICK_LOG_ML} ml"):
                    new_value = int(todays) + DEFAULT_QUICK_LOG_ML
                    if set_today_intake_safe(new_value):
                        st.success(f"Added {DEFAULT_QUICK_LOG_ML} ml")
                        st.experimental_rerun()
            with c2:
                custom_ml = st.number_input("Custom amount (ml)", min_value=0, step=50, value=0, key="custom_ml_input")
                if st.button("Add custom"):
                    if custom_ml > 0:
                        new_value = int(todays) + int(custom_ml)
                        if set_today_intake_safe(new_value):
                            st.success(f"Added {int(custom_ml)} ml")
                            st.experimental_rerun()
                    else:
                        st.warning("Enter value > 0")
            with c3:
                if st.button("Reset today"):
                    if reset_today_intake(st.session_state.uid):
                        st.info("Today's intake reset to 0")
                        st.experimental_rerun()

            st.markdown("---")
            st.subheader("Unit converter")
            conv_col1, conv_col2 = st.columns(2)
            with conv_col1:
                cups = st.number_input("Cups", min_value=0.0, step=0.5, key="conv_cups")
                if st.button("→ Convert to ml"):
                    ml_val = round(cups * CUPS_TO_ML, 1)
                    st.success(f"{cups} cups = {ml_val} ml")
            with conv_col2:
                ml = st.number_input("Milliliters", min_value=0.0, step=50.0, key="conv_ml")
                if st.button("→ Convert to cups", key="conv_to_cups"):
                    cups_val = round(ml / CUPS_TO_ML, 2)
                    st.success(f"{ml} ml = {cups_val} cups")

        elif nav == "Settings":
            st.header("Settings & Profile")
            st.subheader("Age group & daily goal")
            age_choice = st.selectbox("Select age group", list(AGE_GOALS_ML.keys()), index=list(AGE_GOALS_ML.keys()).index(profile.get("age_group","19-50")))
            suggested = AGE_GOALS_ML[age_choice]
            st.write(f"Suggested: {suggested} ml")
            user_goal = st.number_input("Your daily goal (ml)", min_value=500, max_value=10000, value=int(profile.get("user_goal_ml", suggested)), step=50)
            if st.button("Save profile"):
                if update_user_profile(st.session_state.uid, {"age_group": age_choice, "user_goal_ml": int(user_goal)}):
                    st.success("Profile saved.")
                else:
                    st.error("Failed to save profile.")

        elif nav == "Logout":
            st.session_state.logged_in = False
            st.session_state.uid = None
            st.session_state.page = "login"
            st.experimental_rerun()

# small helper to fetch username for display (safe)
def get_username_by_uid(uid):
    user_obj = firebase_read(f"{USERS_NODE}/{uid}")
    if user_obj:
        return user_obj.get("username", "user")
    return "user"

# safe setter that reports errors to user
def set_today_intake_safe(new_value):
    try:
        return set_today_intake(st.session_state.uid, int(new_value))
    except Exception as e:
        st.error("Failed to update intake.")
        return False

# ---------------------------
# App routing
# ---------------------------
if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_ui()
    else:
        login_ui()
else:
    dashboard_ui()
