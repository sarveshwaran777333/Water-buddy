# app.py
"""
WaterBuddy - Robust single-file Streamlit app using Firebase Realtime DB (REST).
Features:
 - Username + password signup/login (no email)
 - Left navigation pane and right content pane after login
 - Age-based suggested goal + manual override
 - +250 ml quick log, custom log, reset today
 - Stores per-day intake under: users/<uid>/days/<YYYY-MM-DD>/intake
 - Progress bar, SVG bottle, unit converter, tips
 - Defensive network/error handling to avoid crashes
Notes:
 - This example stores passwords in plaintext for simplicity (not recommended for production).
 - Make sure your Firebase Realtime DB URL is correct and rules allow the operations used.
"""

import streamlit as st
import requests
import json
from datetime import date
import random
import math
import time

# -----------------------
# Configuration
# -----------------------
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
    "Keep a filled water bottle visible on your desk.",
    "Drink a glass (250 ml) after every bathroom break.",
    "Start your day with a glass of water.",
    "Add lemon or cucumber for natural flavor.",
    "Set small hourly reminders and sip regularly.",
]

REQUEST_TIMEOUT = 8  # seconds

# -----------------------
# Firebase REST helpers (defensive)
# -----------------------
def firebase_url(path: str) -> str:
    # Build URL for Firebase Realtime DB path
    path = path.strip("/")
    return f"{FIREBASE_URL}/{path}.json"

def firebase_get(path: str):
    url = firebase_url(path)
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        else:
            # non-200: return None
            return None
    except requests.RequestException:
        return None

def firebase_put(path: str, value):
    url = firebase_url(path)
    try:
        r = requests.put(url, data=json.dumps(value), timeout=REQUEST_TIMEOUT)
        return r.status_code in (200, 201)
    except requests.RequestException:
        return False

def firebase_patch(path: str, value_dict: dict):
    url = firebase_url(path)
    try:
        r = requests.patch(url, data=json.dumps(value_dict), timeout=REQUEST_TIMEOUT)
        return r.status_code in (200, 201)
    except requests.RequestException:
        return False

def firebase_post(path: str, value):
    url = firebase_url(path)
    try:
        r = requests.post(url, data=json.dumps(value), timeout=REQUEST_TIMEOUT)
        if r.status_code in (200, 201):
            return r.json()  # expected {"name": "<new-key>"}
        return None
    except requests.RequestException:
        return None

# -----------------------
# User management helpers
# -----------------------
def find_user_by_username(username: str):
    """Return (uid, user_dict) or (None, None)."""
    all_users = firebase_get(USERS_NODE)
    if not isinstance(all_users, dict):
        return None, None
    for uid, rec in all_users.items():
        if isinstance(rec, dict) and rec.get("username") == username:
            return uid, rec
    return None, None

def create_user(username: str, password: str):
    """Create user if username not taken. Return uid or None."""
    # Validate locally
    if not username or not password:
        return None
    uid, _ = find_user_by_username(username)
    if uid is not None:
        return None  # already exists
    payload = {
        "username": username,
        "password": password,  # plaintext - for demo only
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
    """Return (True, uid) on success, else (False, None)."""
    uid, rec = find_user_by_username(username)
    if uid and isinstance(rec, dict) and rec.get("password") == password:
        return True, uid
    return False, None

# -----------------------
# Per-day intake helpers
# -----------------------
def get_today_intake(uid: str):
    if not uid:
        return 0
    path = f"{USERS_NODE}/{uid}/days/{DATE_STR}/intake"
    val = firebase_get(path)
    if isinstance(val, (int, float)):
        return int(val)
    # If no value or unexpected type, try to read user root fallback:
    user_rec = firebase_get(f"{USERS_NODE}/{uid}")
    if isinstance(user_rec, dict):
        # support legacy field at root "todays_intake_ml"
        legacy = user_rec.get("todays_intake_ml")
        if isinstance(legacy, (int, float)):
            return int(legacy)
    return 0

def set_today_intake(uid: str, ml_value: int):
    if not uid:
        return False
    ml_value = int(max(0, ml_value))
    path = f"{USERS_NODE}/{uid}/days/{DATE_STR}"
    return firebase_patch(path, {"intake": ml_value})

def reset_today_intake(uid: str):
    return set_today_intake(uid, 0)

# -----------------------
# Profile helpers
# -----------------------
def get_user_profile(uid: str):
    if not uid:
        return {"age_group": "19-50", "user_goal_ml": AGE_GOALS_ML["19-50"]}
    profile = firebase_get(f"{USERS_NODE}/{uid}/profile")
    if isinstance(profile, dict):
        # ensure fields exist
        return {
            "age_group": profile.get("age_group", "19-50"),
            "user_goal_ml": int(profile.get("user_goal_ml", AGE_GOALS_ML["19-50"]))
        }
    return {"age_group": "19-50", "user_goal_ml": AGE_GOALS_ML["19-50"]}

def update_user_profile(uid: str, profile_updates: dict):
    if not uid:
        return False
    return firebase_patch(f"{USERS_NODE}/{uid}/profile", profile_updates)

def get_username_by_uid(uid: str):
    rec = firebase_get(f"{USERS_NODE}/{uid}")
    if isinstance(rec, dict):
        return rec.get("username", "user")
    return "user"

# -----------------------
# UI helpers (SVG bottle)
# -----------------------
def generate_bottle_svg(percent: float, width:int=140, height:int=360) -> str:
    pct = max(0.0, min(100.0, float(percent)))
    inner_w = width - 36
    inner_h = height - 80
    fill_h = (pct / 100.0) * inner_h
    empty_h = inner_h - fill_h
    svg = f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <rect x="12" y="12" rx="20" ry="20" width="{width-24}" height="{height-24}" fill="none" stroke="#1f77b4" stroke-width="4"/>
      <rect x="24" y="36" width="{inner_w}" height="{inner_h}" rx="12" ry="12" fill="#e9f6fb"/>
      <rect x="24" y="{36 + empty_h}" width="{inner_w}" height="{fill_h}" rx="12" ry="12" fill="#2ca6e0"/>
      <text x="{width/2}" y="{height-10}" font-size="14" text-anchor="middle" fill="#023047">{pct:.0f}%</text>
    </svg>
    """
    return svg

# -----------------------
# Streamlit app start
# -----------------------
st.set_page_config(page_title="WaterBuddy", layout="wide")
st.title("WaterBuddy — Hydration Tracker")

# session init
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "uid" not in st.session_state:
    st.session_state.uid = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "tip" not in st.session_state:
    st.session_state.tip = random.choice(TIPS)

# -----------------------
# Login UI
# -----------------------
def login_ui():
    st.header("Login")
    usr = st.text_input("Username", key="login_usr")
    pwd = st.text_input("Password", type="password", key="login_pwd")
    if st.button("Login"):
        if not usr or not pwd:
            st.warning("Please enter both username and password.")
            return
        ok, uid = validate_login(usr.strip(), pwd)
        if ok:
            st.session_state.logged_in = True
            st.session_state.uid = uid
            st.success("Login successful.")
            time.sleep(0.6)
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.write("")
    if st.button("Create new account"):
        st.session_state.page = "signup"
        st.rerun()

# -----------------------
# Signup UI
# -----------------------
def signup_ui():
    st.header("Sign Up (username & password)")
    new_usr = st.text_input("Choose username", key="signup_usr")
    new_pwd = st.text_input("Choose password", type="password", key="signup_pwd")
    if st.button("Register"):
        if not new_usr or not new_pwd:
            st.warning("Enter both username and password.")
            return
        created_uid = create_user(new_usr.strip(), new_pwd)
        if created_uid:
            st.success("Account created. You can now log in.")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("Username already exists or network error.")
    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# -----------------------
# Dashboard UI (left/right)
# -----------------------
def dashboard_ui():
    uid = st.session_state.uid
    profile = get_user_profile(uid)
    intake = get_today_intake(uid)

    left_col, right_col = st.columns([1, 3])

    with left_col:
        st.subheader("Menu")
        nav = st.radio("Navigate", ["Home", "Log Water", "Settings", "Logout"])
        st.markdown("---")
        st.write("Tip of the day")
        st.info(st.session_state.tip)
        if st.button("New tip"):
            st.session_state.tip = random.choice(TIPS)
            st.rerun()
    with right_col:
        if nav == "Home":
            st.header("Today's Summary")
            st.write(f"User: **{get_username_by_uid(uid)}**")
            st.write(f"Date: {DATE_STR}")

            std_goal = AGE_GOALS_ML.get(profile.get("age_group", "19-50"), 2500)
            user_goal = int(profile.get("user_goal_ml", std_goal))

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Standard target")
                st.write(f"**{std_goal} ml**")
            with col2:
                st.subheader("Your target")
                st.write(f"**{user_goal} ml**")

            remaining = max(user_goal - intake, 0)
            percent = min((intake / user_goal) * 100 if user_goal>0 else 0, 100)

            st.metric("Total intake (ml)", f"{intake} ml", delta=f"{remaining} ml to goal" if remaining>0 else "Goal reached!")
            st.progress(percent / 100)

            svg = generate_bottle_svg(percent)
            st.components.v1.html(svg, height=380, scrolling=False)

            if percent >= 100:
                st.success("Amazing! 100% of goal reached.")
            elif percent >= 75:
                st.info("Great! 75% reached.")
            elif percent >= 50:
                st.info("Nice — 50% reached.")
            elif percent >= 25:
                st.info("Good start — 25% reached.")
            else:
                st.write("Let's get started — small sips add up.")

        elif nav == "Log Water":
            st.header("Log Water Intake")
            st.write(f"Today's intake: **{intake} ml**")

            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                if st.button(f"+{DEFAULT_QUICK_LOG_ML} ml"):
                    new_val = intake + DEFAULT_QUICK_LOG_ML
                    ok = set_today_intake(uid, new_val)
                    if ok:
                        st.success(f"Added {DEFAULT_QUICK_LOG_ML} ml.")
                        st.rerun()
                    else:
                        st.error("Failed to update. Check network/DB rules.")
            with c2:
                custom = st.number_input("Custom amount (ml)", min_value=0, step=50, key="custom_input")
                if st.button("Add custom"):
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
                if st.button("Reset today"):
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
                if st.button("Convert cups → ml"):
                    ml_conv = round(cups * CUPS_TO_ML, 1)
                    st.success(f"{cups} cups = {ml_conv} ml")
            with cc2:
                ml_in = st.number_input("Milliliters", min_value=0.0, step=50.0, key="conv_ml")
                if st.button("Convert ml → cups"):
                    cups_conv = round(ml_in / CUPS_TO_ML, 2)
                    st.success(f"{ml_in} ml = {cups_conv} cups")

        elif nav == "Settings":
            st.header("Settings")
            age_choice = st.selectbox("Select age group", list(AGE_GOALS_ML.keys()), index=list(AGE_GOALS_ML.keys()).index(profile.get("age_group","19-50")))
            suggested = AGE_GOALS_ML[age_choice]
            st.write(f"Suggested goal: {suggested} ml")
            user_goal_val = st.number_input("Your daily goal (ml)", min_value=500, max_value=10000, value=int(profile.get("user_goal_ml", suggested)), step=50)
            if st.button("Save"):
                ok = update_user_profile(uid, {"age_group": age_choice, "user_goal_ml": int(user_goal_val)})
                if ok:
                    st.success("Profile saved.")
                else:
                    st.error("Failed to save profile. Check network/DB rules.")

        elif nav == "Logout":
            st.session_state.logged_in = False
            st.session_state.uid = None
            st.session_state.page = "login"
            st.rerun()

# -----------------------
# Routing
# -----------------------
if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_ui()
    else:
        login_ui()
else:
    dashboard_ui()







