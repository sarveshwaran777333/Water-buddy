import streamlit as st
import requests, hashlib, json, datetime
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"

# =========================
# UTILITY FUNCTIONS
# =========================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def firebase_get(path):
    url = f"{FIREBASE_URL}/{path}.json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json() or {}
    else:
        st.error("⚠️ Firebase fetch failed.")
        return {}


def firebase_put(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    requests.put(url, json=data)


def firebase_patch(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    requests.patch(url, json=data)


def get_weather_data(lat, lon):
    """Fetch reliable temperature using Open-Meteo API with fallback."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        r = requests.get(url)
        data = r.json()
        if "current_weather" in data:
            return round(data["current_weather"]["temperature"], 1)
        return 30
    except:
        st.warning("Couldn't fetch weather. Using default 30°C.")
        return 30


def set_goal_based_on_climate(temp):
    """Set goal dynamically based on temperature."""
    if temp >= 35:
        return 3500
    elif temp >= 30:
        return 3000
    elif temp >= 25:
        return 2500
    else:
        return 2000


def apply_theme_and_font(theme, font):
    """Apply app-wide styling."""
    if theme == "Dark":
        st.markdown(
            """
            <style>
            .stApp {background-color: #121212; color: #f5f5f5;}
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            .stApp {background-color: #ffffff; color: #000000;}
            </style>
            """,
            unsafe_allow_html=True,
        )

    font_sizes = {"Small": "14px", "Medium": "16px", "Large": "18px"}
    st.markdown(
        f"""
        <style>
        body, p, div, input, button, label {{
            font-size: {font_sizes.get(font, '16px')} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# =========================
# PAGE FUNCTIONS
# =========================

def login_page():
    st.title("💧 Water Buddy Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users = firebase_get("users")
        if username in users and users[username]["password"] == hash_password(password):
            st.session_state["user"] = username
            st.session_state["page"] = "home"
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid username or password.")

    st.write("Don't have an account?")
    if st.button("Sign Up"):
        st.session_state["page"] = "signup"


def signup_page():
    st.title("🧊 Create Your Water Buddy Account")

    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")

    if st.button("Sign Up"):
        users = firebase_get("users")
        if username in users:
            st.error("Username already exists.")
        else:
            user_data = {
                "password": hash_password(password),
                "goal": 2000,
                "logged": 0,
                "location": "Chennai",
                "lat": 13.0827,
                "lon": 80.2707,
                "theme": "Light",
                "font": "Medium",
                "last_reset": str(datetime.date.today()),
                "history": []
            }
            firebase_patch(f"users/{username}", user_data)
            st.success("✅ Account created! You can now log in.")
            st.session_state["page"] = "login"


def home_page():
    st.title("🏠 Water Buddy Home")

    username = st.session_state["user"]
    user_data = firebase_get(f"users/{username}")

    apply_theme_and_font(user_data["theme"], user_data["font"])

    # Auto-reset every 24 hours
    today = str(datetime.date.today())
    if user_data.get("last_reset") != today:
        user_data["logged"] = 0
        user_data["last_reset"] = today
        firebase_patch(f"users/{username}", user_data)

    st.write("📍 Enter your city:")
    city = st.text_input("City", value=user_data.get("location", "Chennai"))

    if st.button("Update Location"):
        geo = requests.get(f"https://nominatim.openstreetmap.org/search?city={city}&format=json").json()
        if geo:
            lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
            user_data.update({"location": city, "lat": lat, "lon": lon})
            firebase_patch(f"users/{username}", user_data)
            st.success(f"Location updated to {city}!")
        else:
            st.error("Could not find that city. Try again.")

    lat, lon = user_data["lat"], user_data["lon"]
    temp = get_weather_data(lat, lon)
    goal = set_goal_based_on_climate(temp)
    user_data["goal"] = goal
    firebase_patch(f"users/{username}", user_data)

    st.markdown(f"### 🌤️ {user_data['location']}: {temp}°C")
    st.markdown(f"**🎯 Daily Goal:** {goal} ml")
    st.markdown(f"**💧 Logged So Far:** {user_data['logged']} ml")
    st.write("🕒", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    progress = min(user_data["logged"] / goal, 1.0)
    st.progress(progress)
    st.caption(f"{int(progress * 100)}% of your goal achieved!")

    # --- Matplotlib Hydration Chart ---
    fig, ax = plt.subplots(figsize=(5, 2.5))
    ax.bar(["Goal", "Logged"], [goal, user_data["logged"]], color=["#90CAF9", "#42A5F5"])
    ax.set_ylabel("ml")
    ax.set_title("Today's Hydration Progress")
    st.pyplot(fig)

    # Update daily history
    if "history" not in user_data:
        user_data["history"] = []
    if not user_data["history"] or user_data["history"][-1]["date"] != today:
        user_data["history"].append({"date": today, "logged": user_data["logged"]})
        if len(user_data["history"]) > 7:
            user_data["history"].pop(0)
        firebase_patch(f"users/{username}", user_data)

    # Weekly trend chart
    st.subheader("📊 Weekly Hydration Trend")
    dates = [d["date"][-5:] for d in user_data["history"]]
    logged = [d["logged"] for d in user_data["history"]]
    fig2, ax2 = plt.subplots(figsize=(5, 2.5))
    ax2.plot(dates, logged, marker="o", color="#42A5F5")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Water (ml)")
    ax2.set_title("Hydration Over the Last 7 Days")
    st.pyplot(fig2)

    # Add water
    add = st.number_input("Add water intake (ml):", min_value=0)
    if st.button("Log Water"):
        user_data["logged"] += add
        firebase_patch(f"users/{username}", user_data)
        if user_data["logged"] >= goal:
            st.balloons()
            st.success("Goal achieved! 💦")
        st.rerun()

    st.divider()
    if st.button("Go to Tasks 📋"):
        st.session_state["page"] = "tasks"
    if st.button("Settings ⚙️"):
        st.session_state["page"] = "settings"


def tasks_page():
    st.title("📋 Daily Hydration Tasks")
    tasks = [
        "Drink 1 glass after waking up 🌅",
        "Have water before meals 🍽️",
        "Refill your bottle twice 🚰",
        "Avoid sugary drinks 🧃",
        "Drink water before bed 🌙",
    ]
    for t in tasks:
        st.checkbox(t, key=t)
    if st.button("Back to Home 🏠"):
        st.session_state["page"] = "home"


def settings_page():
    st.title("⚙️ Settings")
    username = st.session_state["user"]
    user_data = firebase_get(f"users/{username}")

    apply_theme_and_font(user_data["theme"], user_data["font"])

    st.subheader("🎨 Theme & Font")
    theme = st.radio("Choose Theme:", ["Light", "Dark"], index=(0 if user_data["theme"] == "Light" else 1))
    font = st.radio("Font Size:", ["Small", "Medium", "Large"], index=["Small", "Medium", "Large"].index(user_data["font"]))
    user_data["theme"], user_data["font"] = theme, font
    firebase_patch(f"users/{username}", user_data)

    st.subheader("💧 Water Log Controls")
    if st.button("Reset Daily Log"):
        user_data["logged"] = 0
        firebase_patch(f"users/{username}", user_data)
        st.success("Daily water log reset!")

    st.subheader("🔄 Reset All Settings")
    if st.button("Reset to Default"):
        defaults = {
            "theme": "Light",
            "font": "Medium",
            "goal": 2000,
            "logged": 0,
            "location": "Chennai",
            "lat": 13.0827,
            "lon": 80.2707,
        }
        firebase_patch(f"users/{username}", defaults)
        st.success("Settings restored to default!")
        st.rerun()

    st.divider()
    if st.button("Logout 🚪"):
        st.session_state.clear()
        st.session_state["page"] = "login"
        st.rerun()

# =========================
# MAIN APP CONTROLLER
# =========================
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
