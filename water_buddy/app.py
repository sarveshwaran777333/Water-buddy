# app.py
import streamlit as st
import requests
import json
import hashlib
from datetime import date, datetime

# -------------------------
# CONFIG - set your Firebase URL here
# -------------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"

# -------------------------
# Utilities
# -------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def fetch_user(username: str):
    """Fetch user dict from Firebase (or None if not exists)."""
    try:
        r = requests.get(f"{FIREBASE_URL}/users/{username}.json")
        if r.status_code == 200:
            return r.json()  # None if not exists
    except Exception as e:
        st.error(f"Error contacting Firebase: {e}")
    return None

def save_user(username: str, data: dict):
    """Save full user dict to Firebase using PUT (overwrite)."""
    try:
        # use json param to set proper headers
        r = requests.put(f"{FIREBASE_URL}/users/{username}.json", json=data)
        return r.status_code in (200, 201)
    except Exception as e:
        st.error(f"Error saving to Firebase: {e}")
        return False

def ensure_defaults(user: dict) -> dict:
    """Ensure user dict has all expected keys with defaults."""
    defaults = {
        "password": None,
        "logged": 0,
        "goal": 2000,
        "location": "Chennai",
        "lat": 13.0827,
        "lon": 80.2707,
        "theme": "Light",
        "font": "Medium",
        "last_reset": str(date.today()),
    }
    if user is None:
        return defaults.copy()
    for k, v in defaults.items():
        if k not in user:
            user[k] = v
    return user

def reset_if_new_day(user: dict) -> (dict, bool):
    """If last_reset is not today, reset logged to 0 and update last_reset."""
    today = str(date.today())
    changed = False
    if user.get("last_reset") != today:
        user["logged"] = 0
        user["last_reset"] = today
        changed = True
    return user, changed

def geocode_city(city: str):
    """Return (lat, lon) for a city name using geocode.maps.co (no API key)."""
    try:
        r = requests.get(f"https://geocode.maps.co/search?q={requests.utils.quote(city)}")
        arr = r.json()
        if arr:
            return float(arr[0]["lat"]), float(arr[0]["lon"])
    except Exception:
        pass
    return None, None

def get_weather_data(lat: float, lon: float):
    """Get current temperature using Open-Meteo with hourly fallback."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m"
        )
        r = requests.get(url, timeout=8)
        data = r.json()
        if "current_weather" in data and "temperature" in data["current_weather"]:
            return round(data["current_weather"]["temperature"], 1)
        if "hourly" in data and "temperature_2m" in data["hourly"]:
            temps = data["hourly"]["temperature_2m"]
            if temps:
                return round(temps[-1], 1)
    except Exception:
        pass
    return None

def set_goal_based_on_climate(temp):
    """Return goal ml based on temperature (fallback to 2000 if temp is None)."""
    if temp is None:
        return 2000
    if temp >= 35:
        return 3500
    if temp >= 30:
        return 3000
    if temp >= 25:
        return 2500
    return 2000

def apply_theme_and_font(theme: str, font: str):
    """Apply simple CSS theme and font scaling."""
    if theme == "Dark":
        st.markdown(
            "<style>.stApp { background-color: #121212 !important; color: #f5f5f5 !important; }</style>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<style>.stApp { background-color: #ffffff !important; color: #000000 !important; }</style>",
            unsafe_allow_html=True,
        )

    font_sizes = {"Small": "14px", "Medium": "16px", "Large": "18px"}
    sz = font_sizes.get(font, "16px")
    st.markdown(
        f"""
        <style>
            body, .css-18e3th9, .css-1d391kg, .st-c8 {{ font-size: {sz} !important; }}
            .stButton>button {{ font-size: {sz} !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# -------------------------
# Streamlit App
# -------------------------
st.set_page_config(page_title="💧 WaterHydrator", page_icon="💧", layout="centered")

# initialize session state
if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "username" not in st.session_state:
    st.session_state["username"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None

# -------------------------
# LOGIN / SIGNUP UI
# -------------------------
def login_ui():
    st.title("💧 WaterHydrator — Login")

    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Username")
    with col2:
        password = st.text_input("Password", type="password")

    if st.button("Login"):
        if not username or not password:
            st.error("Enter both username and password.")
            return
        remote = fetch_user(username)
        if remote:
            # remote stores hashed password
            stored_hash = remote.get("password")
            if stored_hash and stored_hash == hash_password(password):
                # Ensure defaults
                remote = ensure_defaults(remote)
                # Auto-reset if new day
                remote, changed = reset_if_new_day(remote)
                if changed:
                    save_user(username, remote)
                st.session_state["username"] = username
                st.session_state["user"] = remote
                st.session_state["page"] = "home"
                st.success(f"Welcome back, {username}!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password.")
        else:
            st.error("User not found. Please sign up.")

    st.markdown("---")
    st.subheader("Create a new account")
    new_user = st.text_input("New username", key="new_user")
    new_pass = st.text_input("New password", type="password", key="new_pass")
    if st.button("Sign Up"):
        if not new_user or not new_pass:
            st.error("Enter username and password to sign up.")
        else:
            if fetch_user(new_user):
                st.error("Username already exists.")
            else:
                # create default user and store hashed password
                user_obj = ensure_defaults(None)
                user_obj["password"] = hash_password(new_pass)
                user_obj["last_reset"] = str(date.today())
                saved = save_user(new_user, user_obj)
                if saved:
                    st.success("Account created. Please login with the new account.")
                else:
                    st.error("Failed to create account. Check Firebase URL & rules.")

# -------------------------
# HOME UI
# -------------------------
def home_ui():
    st.title("🏠 Home — WaterHydrator")

    username = st.session_state["username"]
    user = fetch_user(username)
    if not user:
        st.error("Could not load user data from cloud. Try refreshing.")
        return
    user = ensure_defaults(user)
    # Auto reset if day changed
    user, changed = reset_if_new_day(user)
    if changed:
        save_user(username, user)

    # apply theme & font
    apply_theme_and_font(user.get("theme", "Light"), user.get("font", "Medium"))

    st.write(f"👤 **{username}** — Location: **{user.get('location', 'Chennai')}**")

    # Location / Weather / Goal
    city_col, btn_col = st.columns([3,1])
    with city_col:
        city = st.text_input("City (for weather & goal)", value=user.get("location","Chennai"))
    with btn_col:
        if st.button("Update Location"):
            lat, lon = geocode_city(city)
            if lat and lon:
                user["location"] = city
                user["lat"] = lat
                user["lon"] = lon
                # fetch weather immediately and adjust goal
                temp = get_weather_data(lat, lon)
                if temp is not None:
                    user["goal"] = set_goal_based_on_climate(temp)
                    st.success(f"Location updated: {city} — {temp}°C — goal {user['goal']} ml")
                else:
                    st.success(f"Location updated: {city} (weather unavailable)")
                save_user(username, user)
                st.experimental_rerun()
            else:
                st.error("Could not geocode that city. Try a different name.")

    lat = user.get("lat", 13.0827)
    lon = user.get("lon", 80.2707)
    temp = get_weather_data(lat, lon)
    if temp is None:
        temp_display = "N/A"
    else:
        temp_display = f"{temp}°C"
    st.markdown(f"### 🌤️ {user.get('location', 'Chennai')}: {temp_display}")

    # ensure goal based on latest temp (but do not overwrite user goal unless Update Location pressed)
    computed_goal = set_goal_based_on_climate(temp) if temp is not None else user.get("goal", 2000)
    # show goal and logged
    goal = user.get("goal", computed_goal)
    logged = user.get("logged", 0)

    st.markdown(f"**🎯 Daily Goal:** {goal} ml")
    st.markdown(f"**💧 Logged Today:** {logged} ml")
    st.write("🕒", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # progress bar
    progress = min(logged / max(goal,1), 1.0)
    st.progress(progress)
    st.caption(f"{int(progress*100)}% of goal")

    # logging intake
    add = st.number_input("Add water (ml)", min_value=0, max_value=2000, value=200, step=50)
    if st.button("Log Water"):
        logged += add
        user["logged"] = logged
        save_user(username, user)
        st.success(f"Logged {add} ml. Total today: {logged} ml")
        st.experimental_rerun()

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    if c1.button("Tasks 📋"):
        st.session_state["page"] = "tasks"
        st.experimental_rerun()
    if c2.button("Settings ⚙️"):
        st.session_state["page"] = "settings"
        st.experimental_rerun()
    if c3.button("Logout 🚪"):
        st.session_state["username"] = None
        st.session_state["user"] = None
        st.session_state["page"] = "login"
        st.experimental_rerun()

# -------------------------
# TASKS UI
# -------------------------
def tasks_ui():
    st.title("📋 Hydration Tasks")
    st.write("Small, actionable daily tasks — check as you complete them.")
    tasks = [
        "Drink a glass of water after waking up",
        "Refill your bottle once before lunch",
        "Have water before each meal",
        "Avoid sugary drinks",
        "Drink a glass before bed"
    ]
    for t in tasks:
        st.checkbox(t, key=t)
    st.markdown("---")
    if st.button("Back to Home"):
        st.session_state["page"] = "home"
        st.experimental_rerun()

# -------------------------
# SETTINGS UI
# -------------------------
def settings_ui():
    st.title("⚙️ Settings")

    username = st.session_state["username"]
    user = fetch_user(username)
    if not user:
        st.error("Could not load user data.")
        return
    user = ensure_defaults(user)

    # show current theme/font and allow change
    st.subheader("Appearance")
    theme = st.radio("Theme:", ["Light", "Dark"], index=0 if user.get("theme","Light")=="Light" else 1)
    font = st.radio("Font size:", ["Small", "Medium", "Large"], index=["Small","Medium","Large"].index(user.get("font","Medium")))
    user["theme"] = theme
    user["font"] = font

    st.subheader("Water / Reset")
    if st.button("Reset today's water (manual)"):
        user["logged"] = 0
        user["last_reset"] = str(date.today())
        save_user(username, user)
        st.success("Today's water log reset.")
    if st.button("Reset settings to default"):
        # keep password
        pw = user.get("password")
        new = ensure_defaults(None)
        new["password"] = pw
        new["last_reset"] = str(date.today())
        save_user(username, new)
        st.success("Settings reset to defaults.")
        st.experimental_rerun()

    # Adjust goal manually
    st.subheader("Goal & Location")
    new_goal = st.number_input("Set daily goal (ml):", min_value=1000, max_value=8000, value=user.get("goal",2000), step=100)
    if st.button("Update Goal"):
        user["goal"] = new_goal
        save_user(username, user)
        st.success("Goal updated.")
    # change location manually
    city = st.text_input("Change location (city):", value=user.get("location","Chennai"))
    if st.button("Update Location & Weather"):
        lat, lon = geocode_city(city)
        if lat and lon:
            user["location"] = city
            user["lat"] = lat
            user["lon"] = lon
            temp = get_weather_data(lat, lon)
            if temp is not None:
                user["goal"] = set_goal_based_on_climate(temp)
            save_user(username, user)
            st.success(f"Location updated: {city}")
            st.experimental_rerun()
        else:
            st.error("Could not geocode that city.")

    st.markdown("---")
    if st.button("Back to Home"):
        st.session_state["page"] = "home"
        st.experimental_rerun()

# -------------------------
# App Router
# -------------------------
if st.session_state["page"] == "login":
    login_ui()
elif st.session_state["page"] == "home":
    # ensure logged-in
    if not st.session_state.get("username"):
        st.session_state["page"] = "login"
        st.experimental_rerun()
    home_ui()
elif st.session_state["page"] == "tasks":
    # ensure logged-in
    if not st.session_state.get("username"):
        st.session_state["page"] = "login"
        st.experimental_rerun()
    tasks_ui()
elif st.session_state["page"] == "settings":
    # ensure logged-in
    if not st.session_state.get("username"):
        st.session_state["page"] = "login"
        st.experimental_rerun()
    settings_ui()
