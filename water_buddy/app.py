import streamlit as st
import json, os, hashlib
from datetime import datetime, timedelta
from meteostat import Stations, Daily
from geopy.geocoders import Nominatim

def get_coordinates_from_city(city):
    """Get latitude and longitude from a city name."""
    try:
        geolocator = Nominatim(user_agent="waterbuddy")
        location = geolocator.geocode(city)
        if location:
            return (location.latitude, location.longitude)
        else:
            st.warning("City not found. Using default (Chennai).")
            return (13.0827, 80.2707)
    except Exception as e:
        st.error(f"Error getting coordinates: {e}")
        return (13.0827, 80.2707)


def get_weather_data(lat, lon):
    """Fetch weather data from meteostat."""
    try:
        end = datetime.today()
        start = end - timedelta(days=1)
        stations = Stations()
        station = stations.nearby(lat, lon).fetch(1)
        if station.empty:
            st.warning("No nearby weather station found.")
            return None

        station_id = station.index[0]
        data = Daily(station_id, start, end).fetch()

        if not data.empty and 'tavg' in data.columns:
            temperature = round(data['tavg'].dropna().iloc[-1], 1)
            return temperature
        else:
            st.warning("No recent weather data available. Using default temperature 30°C.")
            return 30.0  # default fallback
    except Exception as e:
        st.error(f"Error fetching weather data: {e}")
        return None
def set_goal_based_on_climate(temp):
    """Adjust water goal based on temperature."""
    if temp is None:
        return 2000
    elif temp >= 35:
        return 3500
    elif temp >= 30:
        return 3000
    elif temp >= 25:
        return 2500
    else:
        return 2000


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def load_users():
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)


# ---------------------------
# Pages
# ---------------------------

def login_page():
    st.title("💧 Water Buddy Login")
    users = load_users()
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and users[username]["password"] == hash_password(password):
            st.session_state["user"] = username
            st.success("Login successful!")
            st.session_state["page"] = "home"
        else:
            st.error("Invalid username or password.")

    st.write("Don't have an account?")
    if st.button("Sign Up"):
        st.session_state["page"] = "signup"


def signup_page():
    st.title("🧊 Create Your Water Buddy Account")
    users = load_users()
    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")

    if st.button("Sign Up"):
        if username in users:
            st.error("Username already exists.")
        else:
            users[username] = {
                "password": hash_password(password),
                "goal": 2000,
                "logged": 0,
                "theme": "Light",
                "font_size": "Medium"
            }
            save_users(users)
            st.success("Account created! You can now log in.")
            st.session_state["page"] = "login"


def home_page():
    st.title("🏠 Water Buddy Home")

    users = load_users()
    username = st.session_state["user"]
    user_data = users.get(username, {"goal": 2000, "logged": 0})

    city = st.text_input("Enter your city:", value="Chennai")
    if st.button("Get Weather"):
        lat, lon = get_coordinates_from_city(city)
        temp = get_weather_data(lat, lon)
        goal = set_goal_based_on_climate(temp)
        user_data["goal"] = goal
        save_users(users)
        st.success(f"Updated goal based on temperature in {city}!")

    st.write(f"🎯 Daily Goal: {user_data['goal']} ml")
    st.write(f"💧 Water Logged: {user_data['logged']} ml")
    st.write("🕒 Local time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    add = st.number_input("Log water intake (ml):", min_value=0)
    if st.button("Log Water"):
        user_data["logged"] += add
        if user_data["logged"] >= user_data["goal"]:
            st.balloons()
            st.success("Goal achieved! Great job staying hydrated 💦")
        save_users(users)
        st.rerun()

    st.button("🧾 Go to Task Page", on_click=lambda: st.session_state.update(page="tasks"))
    st.button("⚙️ Go to Settings", on_click=lambda: st.session_state.update(page="settings"))


def tasks_page():
    st.title("🧾 Daily Hydration Tasks")
    st.write("Complete hydration challenges to stay on track:")

    tasks = {
        "Refill your water bottle every 2 hours.",
        "Take a short walk and drink water after.",
        "Eat a hydrating fruit like watermelon or cucumber.",
        "Set a reminder to drink water every hour."
        "Drink 200ml of water now"
        "Get hydrated by drinking 500ml of water now"
    }

    for task, amount in tasks.items():
        if task not in st.session_state:
            st.session_state[task] = False

        if st.checkbox(task, value=st.session_state[task], key=task):
            st.session_state["selected_task"] = task
            st.session_state["required_amount"] = amount
            st.session_state["from_task"] = True
            st.session_state[task] = True
            st.session_state["page"] = "home"
            st.rerun()

    st.button("🏠 Back to Home", on_click=lambda: st.session_state.update(page="home"))
    st.button("⚙️ Settings", on_click=lambda: st.session_state.update(page="settings"))        "Drink 1 glass of water as soon as you wake up.",


def settings_page():
    st.title("⚙️ Settings")
    users = load_users()
    username = st.session_state["user"]
    user_data = users[username]

    # Theme and Font Selection
    theme = st.selectbox("Select Theme:", ["Light", "Dark", "Aqua"],
                         index=["Light", "Dark", "Aqua"].index(user_data.get("theme", "Light")))
    font_size = st.selectbox("Font Size:", ["Small", "Medium", "Large"],
                             index=["Small", "Medium", "Large"].index(user_data.get("font_size", "Medium")))

    if st.button("💾 Apply Settings"):
        user_data["theme"] = theme
        user_data["font_size"] = font_size
        save_users(users)
        st.success("Settings updated!")

    # Manual reset of daily log
    if st.button("🔁 Reset Daily Water Log"):
        user_data["logged"] = 0
        save_users(users)
        st.success("Daily log reset!")

    # Reset all settings to default
    if st.button("♻️ Reset Settings to Default"):
        user_data["theme"] = "Light"
        user_data["font_size"] = "Medium"
        user_data["goal"] = 2000
        save_users(users)
        st.success("All settings restored to default!")

    if st.button("🔒 Logout"):
        st.session_state.clear()
        st.session_state["page"] = "login"
        st.rerun()

    # Apply theme effects visually
    if theme == "Dark":
        st.markdown("<style>body {color: white; background-color: #1e1e1e;}</style>", unsafe_allow_html=True)
    elif theme == "Aqua":
        st.markdown("<style>body {color: #005f73; background-color: #d9fdfc;}</style>", unsafe_allow_html=True)
    else:
        st.markdown("<style>body {color: black; background-color: white;}</style>", unsafe_allow_html=True)

    if font_size == "Small":
        st.markdown("<style>body {font-size: 14px;}</style>", unsafe_allow_html=True)
    elif font_size == "Medium":
        st.markdown("<style>body {font-size: 16px;}</style>", unsafe_allow_html=True)
    else:
        st.markdown("<style>body {font-size: 18px;}</style>", unsafe_allow_html=True)


# ---------------------------
# Main App Controller
# ---------------------------

if "page" not in st.session_state:
    st.session_state["page"] = "login"

if st.session_state["page"] == "login":
    login_page()
elif st.session_state["page"] == "signup":
    signup_page()
elif st.session_state["page"] == "home":
    home_page()
elif st.session_state["page"] == "tasks":
    tasks_page()
elif st.session_state["page"] == "settings":
    settings_page()




