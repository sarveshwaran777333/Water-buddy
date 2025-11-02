# app.py
import streamlit as st
import json, os, time, hashlib, requests
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# -------------------------
# Constants & files
# -------------------------
USER_FILE = "users.json"
DEFAULT_DAILY_BASE = 1500  # base ml used in calculation

# -------------------------
# Utilities: data persistence
# -------------------------
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_users(data):
    with open(USER_FILE, "w") as f:
        json.dump(data, f, indent=2)

def hash_password(pwd):
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

# -------------------------
# Location helper (ipinfo fallback)
# -------------------------
def detect_location():
    try:
        r = requests.get("https://ipinfo.io/json", timeout=4)
        if r.status_code == 200:
            d = r.json()
            city = d.get("city") or ""
            region = d.get("region") or ""
            country = d.get("country") or ""
            loc = ", ".join(x for x in [city, region, country] if x)
            return loc
    except Exception:
        pass
    return ""

# -------------------------
# Goal calculation
# -------------------------
def calculate_daily_goal(age=18, health_issues="", temp_c=None):
    base = DEFAULT_DAILY_BASE
    try:
        age = int(age)
    except:
        age = 18
    if age < 18:
        base += 500
    elif age > 60:
        base += 300
    if health_issues:
        hi = health_issues.lower()
        if "diabetes" in hi:
            base += 300
        if "kidney" in hi:
            base -= 300
    if temp_c is not None:
        try:
            t = float(temp_c)
            if t > 30:
                base += 700
            elif t > 20:
                base += 300
        except:
            pass
    return max(base, 1000)

# -------------------------
# Daily reset (enforced)
# -------------------------
def enforce_daily_reset(user):
    today_str = date.today().isoformat()
    if user.get("last_date") != today_str:
        user["water_intake"] = 0
        user["history"] = []
        # reset daily task completions but keep task definitions
        user_tasks = user.get("tasks", {})
        for k in user_tasks:
            user_tasks[k]["done_today"] = False
            user_tasks[k]["reward_claimed"] = False
        user["last_date"] = today_str

# -------------------------
# Animation: simple progress fill
# -------------------------
def animate_fill(old_val, new_val, goal, placeholder_key):
    # placeholder_key is a st.empty() object
    old_pct = min(round((old_val/goal)*100), 100) if goal else 0
    new_pct = min(round((new_val/goal)*100), 100) if goal else 0
    step = 1 if new_pct >= old_pct else -1
    progress_bar = placeholder_key.progress(old_pct)
    text = placeholder_key.empty()
    for p in range(old_pct, new_pct + step, step):
        progress_bar.progress(p)
        text.markdown(f"**Progress:** {p}%  •  {min(int((p/100)*goal), new_val)} / {goal} ml")
        time.sleep(0.02)
    # final
    progress_bar.progress(new_pct)
    text.markdown(f"**Progress:** {new_pct}%  •  {min(int((new_pct/100)*goal), new_val)} / {goal} ml")

# -------------------------
# Default tasks (template)
# -------------------------
DEFAULT_TASKS = {
    "Drink 250 ml now": {"amount": 250, "done_today": False, "reward_claimed": False, "coins": 5},
    "Drink 500 ml after workout": {"amount": 500, "done_today": False, "reward_claimed": False, "coins": 10},
    "Take a 1-minute water break": {"amount": 0, "done_today": False, "reward_claimed": False, "coins": 2},
}

# -------------------------
# App helpers: user lifecycle
# -------------------------
def ensure_user_structure(users, email):
    if email not in users:
        users[email] = {
            "password": "",  # hashed
            "profile": {"name": "", "age": 18, "health_issues": ""},
            "settings": {"font_size": 16, "theme": "Light"},
            "water_intake": 0,
            "history": [],
            "tasks": DEFAULT_TASKS.copy(),
            "coins": 0,
            "last_date": date.today().isoformat()
        }
    else:
        # ensure keys exist
        user = users[email]
        user.setdefault("profile", {"name": "", "age": 18, "health_issues": ""})
        user.setdefault("settings", {"font_size": 16, "theme": "Light"})
        user.setdefault("water_intake", 0)
        user.setdefault("history", [])
        user.setdefault("tasks", DEFAULT_TASKS.copy())
        user.setdefault("coins", 0)
        user.setdefault("last_date", date.today().isoformat())

# -------------------------
# Streamlit UI pages
# -------------------------
st.set_page_config(page_title="Water Buddy", page_icon="💧", layout="centered")

# autorefresh to keep time updated (optional)
st_autorefresh(interval=60 * 1000, key="auto_refresh")

# Initialize session state
if "email" not in st.session_state:
    st.session_state.email = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "users" not in st.session_state:
    st.session_state.users = load_users()
if "page" not in st.session_state:
    st.session_state.page = "login"

# top layout: simple header style from settings
def apply_user_style():
    users = st.session_state.users
    email = st.session_state.email
    if email and email in users:
        s = users[email].get("settings", {})
        fs = s.get("font_size", 16)
        theme = s.get("theme", "Light")
        bg = "#0f172a" if theme == "Dark" else "#ffffff"
        color = "#ffffff" if theme == "Dark" else "#000000"
        st.markdown(f"""
            <style>
            .stApp {{
                background-color: {bg};
                color: {color};
            }}
            .block-container {{
                font-size: {fs}px;
            }}
            </style>
        """, unsafe_allow_html=True)

# ---------- Authentication pages ----------
def signup_box():
    st.subheader("Sign up")
    email = st.text_input("Email for sign up", key="su_email")
    pwd = st.text_input("Create a password", type="password", key="su_pwd")
    name = st.text_input("Full name (optional)", key="su_name")
    age = st.number_input("Age", min_value=1, max_value=120, value=18, key="su_age")
    if st.button("Create account"):
        if not email or not pwd:
            st.warning("Please provide email and password.")
            return
        users = st.session_state.users
        if email in users and users[email].get("password"):
            st.error("This email already has an account. Please log in.")
            return
        ensure_user_structure(users, email)
        users[email]["password"] = hash_password(pwd)
        users[email]["profile"].update({"name": name or "", "age": age})
        save_users(users)
        st.success("Account created! You can now login.")
        st.session_state.page = "login"
        st.experimental_rerun()

def login_box():
    st.subheader("Login")
    email = st.text_input("Email", key="li_email")
    pwd = st.text_input("Password", type="password", key="li_pwd")
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Login"):
            users = st.session_state.users
            if email in users and users[email].get("password") == hash_password(pwd):
                st.session_state.logged_in = True
                st.session_state.email = email
                ensure_user_structure(users, email)
                # enforce daily reset
                enforce_daily_reset(users[email])
                save_users(users)
                st.success("Logged in")
                st.session_state.page = "home"
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")
    with col2:
        if st.button("Go to Sign up"):
            st.session_state.page = "signup"
            st.experimental_rerun()

# ---------- Home page ----------
def home_page():
    apply_user_style()
    st.title("Home — Water Buddy")
    users = st.session_state.users
    email = st.session_state.email
    user = users[email]

    # Left and right layout
    col1, col2 = st.columns([1, 2])
    with col1:
        st.header(user["profile"].get("name") or email)
        st.write(f"Age: {user['profile'].get('age', '')}")
        st.write(f"Coins: {user.get('coins',0)}")

        # Detect location (auto or manual)
        if "detected_location" not in st.session_state:
            st.session_state.detected_location = detect_location()
        loc = st.session_state.detected_location
        location_input = st.text_input("Your location (detected / manual)", value=loc or "", key="loc_input")

        # Detect current weather using Meteostat
        try:
            from meteostat import Stations, Daily
            import pandas as pd
            from datetime import datetime

            if location_input:
                stations = Stations().nearby_name(location_input)
                station = stations.fetch(1)
                if not station.empty:
                    lat = station.iloc[0].lat
                    lon = station.iloc[0].lon
                    # Get today's weather data
                    start = end = datetime.today()
                    data = Daily(station, start, end)
                    data = data.fetch()
                    if not data.empty:
                        temp_c = round(data['tavg'].iloc[0], 1) if 'tavg' in data.columns else 30
                        st.success(f"🌡 Current Temp at {location_input}: {temp_c}°C")
                    else:
                        temp_c = 30
                        st.warning("Couldn’t fetch temperature data. Using default 30°C.")
                else:
                    temp_c = 30
                    st.warning("No nearby weather station found. Using default temperature.")
            else:
                temp_c = 30
                st.warning("Enter a location to detect weather.")
        except Exception as e:
            st.error("Error fetching weather data.")
            temp_c = 30

        # Show current date/time
        st.write("Local time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    with col2:
        # Calculate and display goal dynamically
        goal = calculate_daily_goal(
            age=user["profile"].get("age",18),
            health_issues=user["profile"].get("health_issues",""),
            temp_c=temp_c
        )
        st.subheader("Your Water Goal 💧")
        st.write(f"Based on current temperature: **{temp_c}°C**")
        st.write(f"Recommended Daily Goal: **{goal} ml**")
        st.write(f"Today's Intake: **{user.get('water_intake',0)} ml**")

        # Water logging
        intake_amt = st.number_input("Log water (ml)", min_value=0, step=50, value=250, key="log_input")
        if st.button("Add Intake"):
            old = user.get("water_intake",0)
            user["water_intake"] = old + int(intake_amt)
            user["history"].append({"time": datetime.now().isoformat(), "amount": int(intake_amt)})
            save_users(users)
            placeholder = st.empty()
            animate_fill(old, user["water_intake"], goal, placeholder)
            st.success(f"Logged {int(intake_amt)} ml.")

        # Progress bar
        pct = min(round((user.get("water_intake",0)/goal)*100),100) if goal else 0
        st.progress(pct)
        if pct >= 100:
            st.balloons()
            st.info("Goal achieved! Well done 💦")

# ---------- Tasks page ----------
def tasks_page():
    apply_user_style()
    st.title("Tasks — Daily Actions")
    users = st.session_state.users
    email = st.session_state.email
    user = users[email]
    st.write("Click a task to go to Home and log the suggested amount. After logging, come back to claim reward.")

    for task_name, tinfo in user.get("tasks", {}).items():
        col1, col2 = st.columns([3,1])
        with col1:
            status = "✅ Completed" if tinfo.get("done_today") else "🔲 Not done"
            st.markdown(f"**{task_name}** — {status}")
            st.write(f"Suggested: {tinfo.get('amount')} ml • Reward: {tinfo.get('coins')} coins")
        with col2:
            if not tinfo.get("done_today"):
                if st.button(f"Do: {task_name}", key=f"do_{task_name}"):
                    # navigate to home and prefill log_input by storing a session flag
                    st.session_state.task_to_do = {"name": task_name, "amount": tinfo.get("amount",0)}
                    st.session_state.page = "home"
                    st.experimental_rerun()
            else:
                if not tinfo.get("reward_claimed"):
                    if st.button(f"Claim ({tinfo.get('coins')}c)", key=f"claim_{task_name}"):
                        user["coins"] = user.get("coins",0) + tinfo.get("coins",0)
                        tinfo["reward_claimed"] = True
                        save_users(users)
                        st.success(f"Claimed {tinfo.get('coins')} coins!")
                else:
                    st.write("Reward claimed")

# ---------- Settings page ----------
def settings_page():
    apply_user_style()
    st.title("Settings")
    users = st.session_state.users
    email = st.session_state.email
    user = users[email]
    profile = user.get("profile",{})
    settings = user.get("settings",{})

    st.subheader("Profile")
    name = st.text_input("Name", value=profile.get("name",""))
    age = st.number_input("Age", min_value=1, max_value=120, value=profile.get("age",18))
    health = st.text_input("Health issues (optional)", value=profile.get("health_issues",""))

    st.subheader("Appearance & Preferences")
    font_size = st.slider("Font size", 12, 24, value=settings.get("font_size",16))
    theme = st.radio("Theme", ["Light","Dark"], index=0 if settings.get("theme","Light")=="Light" else 1)

    st.subheader("App Controls")
    if st.button("Save settings"):
        profile.update({"name": name, "age": age, "health_issues": health})
        settings.update({"font_size": font_size, "theme": theme})
        user["profile"] = profile
        user["settings"] = settings
        # recalculate daily goal immediately (but stored goal is dynamic)
        save_users(users)
        st.success("Settings saved.")
        st.experimental_rerun()

    if st.button("Reset daily water intake (today only)"):
        user["water_intake"] = 0
        user["history"] = []
        for k in user["tasks"]:
            user["tasks"][k]["done_today"] = False
            user["tasks"][k]["reward_claimed"] = False
        save_users(users)
        st.success("Today's progress reset.")

    if st.button("Reset all settings to default"):
        user["settings"] = {"font_size":16, "theme":"Light"}
        user["profile"]["health_issues"] = ""
        save_users(users)
        st.success("Settings reset to defaults.")
        st.experimental_rerun()

# ---------- Flow control ----------
def logout():
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.page = "login"
    st.experimental_rerun()

# Main layout
st.sidebar.title("Water Buddy")
if not st.session_state.logged_in:
    st.sidebar.write("Not logged in")
else:
    st.sidebar.write(f"Logged in as: {st.session_state.email}")
    if st.sidebar.button("Logout"):
        logout()

# Simple nav (visible when logged in)
if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        signup_box()
    else:
        login_box()
else:
    # if user came from a task "Do" button with a prefilled task
    if "task_to_do" in st.session_state and st.session_state.page == "home":
        # prefill the log input on home page by setting its default via session_state
        task = st.session_state.pop("task_to_do", None)
        if task:
            # mark task done when exact amount logged: we'll rely on the user logging the amount
            # We place a hint in the session so home_page shows a notice (home page uses session state log hint)
            st.session_state.prefill_amount = task.get("amount",0)
            st.session_state.prefill_task_name = task.get("name","")
    # show navigation
    page = st.sidebar.radio("Navigate", ["home","tasks","settings"], index=["home","tasks","settings"].index(st.session_state.get("page","home")))
    st.session_state.page = page
    # ensure user structure and daily reset
    ensure_user_structure(st.session_state.users, st.session_state.email)
    enforce_daily_reset(st.session_state.users[st.session_state.email])
    save_users(st.session_state.users)

    if st.session_state.page == "home":
        # if there's a prefill amount from tasks
        if "prefill_amount" in st.session_state and st.session_state.prefill_amount:
            # notify user
            st.info(f"Task: log {st.session_state.prefill_amount} ml in Home to complete the task '{st.session_state.get('prefill_task_name','')}'.")
        home_page()
        # after home page (user may have logged water), check if prefill completed:
        users = st.session_state.users
        user = users[st.session_state.email]
        if "prefill_amount" in st.session_state:
            amt = st.session_state.prefill_amount
            # if user's water intake increased and now contains that amt in recent history, mark task done
            if user.get("history") and any(h.get("amount",0) >= amt for h in user.get("history")[-3:]):
                tn = st.session_state.get("prefill_task_name")
                if tn and tn in user["tasks"]:
                    user["tasks"][tn]["done_today"] = True
                    save_users(users)
                    st.success(f"Task '{tn}' marked completed. Come to Tasks page to claim reward.")
                    # clear prefill
                st.session_state.pop("prefill_amount", None)
                st.session_state.pop("prefill_task_name", None)

    elif st.session_state.page == "tasks":
        tasks_page()
    elif st.session_state.page == "settings":
        settings_page()

