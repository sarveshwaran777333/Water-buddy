import streamlit as st
import json, os, datetime, random
from pyowm import OWM
from pyowm.utils.config import get_default_config
from meteostat import Point, Daily

# -----------------------
# Data Management
# -----------------------
DATA_FILE = "users.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# -----------------------
# WEATHER SYSTEM
# -----------------------
def get_weather_pyowm(city):
    """Fetch current weather using PyOWM demo key"""
    try:
        config_dict = get_default_config()
        config_dict['language'] = 'en'
        owm = OWM('b6907d289e10d714a6e88b30761fae22')  # public demo key
        mgr = owm.weather_manager()
        obs = mgr.weather_at_place(city)
        w = obs.weather
        temp = w.temperature('celsius')['temp']
        status = w.detailed_status
        return f"{status.title()} — {temp:.1f}°C"
    except Exception:
        return None

def get_weather_meteostat(lat, lon):
    """Fallback using Meteostat"""
    try:
        location = Point(lat, lon)
        start = datetime.datetime.now() - datetime.timedelta(days=1)
        end = datetime.datetime.now()
        data = Daily(location, start, end).fetch()
        if not data.empty:
            temp = data['tavg'].iloc[-1]
            return f"Clear Sky — {temp:.1f}°C"
        else:
            return "Weather data unavailable"
    except Exception:
        return "Weather data unavailable"

# -----------------------
# AUTH SYSTEM
# -----------------------
def login_signup_page():
    users = load_data()
    st.title("💧 Water Hydrator Login / Sign Up")

    mode = st.radio("Choose an option", ["Login", "Sign Up"])

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if mode == "Sign Up":
        name = st.text_input("Name")
        age = st.number_input("Age", 5, 100)
        if st.button("Create Account"):
            if email in users:
                st.warning("Account already exists.")
            else:
                users[email] = {
                    "password": password,
                    "name": name,
                    "age": age,
                    "intake": 0,
                    "goal": 2000,
                    "tasks_state": {},
                    "settings": {
                        "font_size": "Medium",
                        "theme": "Light",
                        "mascot": "🐬",
                        "health_issues": ""
                    }
                }
                save_data(users)
                st.success("Account created! Please login.")

    if mode == "Login":
        if st.button("Login"):
            if email in users and users[email]["password"] == password:
                st.session_state.user = email
                st.session_state.page = "Dashboard"
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")

# -----------------------
# DASHBOARD
# -----------------------
def dashboard_page():
    users = load_data()
    user = users[st.session_state.user]
    st.title("💧 Water Hydrator Dashboard")
    st.write(f"Welcome, {user['name']}!")

    st.write(f"🕒 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    st.subheader("Enter Water Intake")
    intake = st.number_input("Enter amount (ml):", 0, 5000)
    if st.button("Add Water"):
        user["intake"] += intake
        save_data(users)
        st.success(f"Added {intake} ml water!")

    st.progress(user["intake"] / user["goal"])
    st.write(f"💧 Total Intake: {user['intake']} / {user['goal']} ml")

    if user["intake"] >= user["goal"]:
        st.balloons()
        st.success("🎉 Goal completed! Great job!")

# -----------------------
# TASK PAGE
# -----------------------
def tasks_page():
    st.title("✅ Daily Tasks")
    users = load_data()
    user = users[st.session_state.user]
    tasks = ["Drink 500 ml water", "Drink 1 litre water", "Complete daily goal"]

    for task in tasks:
        completed = user["tasks_state"].get(task, False)
        if completed:
            st.success(f"✅ {task} — Completed!")
        else:
            if st.button(f"Mark '{task}' Complete"):
                user["tasks_state"][task] = True
                save_data(users)
                st.session_state.page = "Dashboard"
                st.experimental_rerun()

# -----------------------
# SETTINGS PAGE
# -----------------------
def settings_page():
    users = load_data()
    user = users[st.session_state.user]
    st.title("⚙️ Settings")

    st.subheader("Display Options")
    font_size = st.selectbox("Font Size", ["Small", "Medium", "Large"], index=["Small","Medium","Large"].index(user["settings"]["font_size"]))
    theme = st.selectbox("Theme", ["Light", "Dark"], index=["Light","Dark"].index(user["settings"]["theme"]))

    st.subheader("Profile Settings")
    age = st.number_input("Age", 5, 100, user["age"])
    mascot = st.selectbox("Choose Mascot", ["🐬 Dolphin", "🐟 Fish", "🤖 Robot", "🐢 Tortoise", "💧 Water Drop"])
    health_issues = st.text_area("Health Issues (optional)", user["settings"]["health_issues"])

    if st.button("Save Settings"):
        user["age"] = age
        user["settings"]["font_size"] = font_size
        user["settings"]["theme"] = theme
        user["settings"]["mascot"] = mascot.split()[0]
        user["settings"]["health_issues"] = health_issues
        save_data(users)
        st.success("Settings saved successfully!")

    if st.button("Reset All Data"):
        user["intake"] = 0
        user["tasks_state"] = {}
        save_data(users)
        st.warning("All progress reset!")

# -----------------------
# WEATHER PAGE
# -----------------------
def weather_page():
    st.title("🌍 Weather Info")
    location_type = st.radio("Enter Location By:", ["City Name", "Coordinates"])

    if location_type == "City Name":
        city = st.text_input("Enter City:")
        if st.button("Get Weather"):
            weather = get_weather_pyowm(city)
            if weather:
                st.success(f"🌦️ {city}: {weather}")
            else:
                st.warning("Could not fetch weather. Try coordinates.")

    else:
        lat = st.number_input("Latitude", format="%.4f")
        lon = st.number_input("Longitude", format="%.4f")
        if st.button("Get Weather"):
            weather = get_weather_meteostat(lat, lon)
            st.info(f"📍 ({lat}, {lon}) — {weather}")

# -----------------------
# MAIN APP
# -----------------------
def main():
    st.set_page_config(page_title="Water Hydrator", page_icon="💧")

    if "user" not in st.session_state:
        login_signup_page()
        return

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    st.sidebar.title("💧 Navigation")
    st.sidebar.write(f"👤 {st.session_state.user}")
    page = st.sidebar.radio("Go to", ["Dashboard", "Tasks", "Settings", "Weather", "Logout"])

    if page == "Dashboard": dashboard_page()
    elif page == "Tasks": tasks_page()
    elif page == "Settings": settings_page()
    elif page == "Weather": weather_page()
    elif page == "Logout":
        st.session_state.clear()
        st.experimental_rerun()

if __name__ == "__main__":
    main()
