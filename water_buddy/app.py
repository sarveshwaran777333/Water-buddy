import streamlit as st
import requests
import datetime
import matplotlib.pyplot as plt
import hashlib

# =========================
# CONFIG
# =========================
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"

# =========================
# AGE GROUPS -> GOAL (mL)
# =========================
AGE_GROUP_GOALS_ML = {
    "age 6-12": 2000,
    "age 13-18": 2500,
    "age 19-50": 3000,
    "Older adults (65+)": 35000,  # chosen midpoint in 2000-2500 range
    "None / Prefer climate-based": None
}

AGE_GROUP_OPTIONS = list(AGE_GROUP_GOALS_ML.keys())

# =========================
# UTILITY FUNCTIONS
# =========================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def firebase_get(path):
    url = f"{FIREBASE_URL}/{path}.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json() or {}
        else:
            st.error("⚠️ Firebase fetch failed.")
            return {}
    except:
        st.warning("⚠️ Unable to connect to Firebase.")
        return {}


def firebase_patch(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    try:
        requests.patch(url, json=data, timeout=10)
    except:
        st.warning("⚠️ Firebase update failed.")


def get_weather_data(lat, lon):
    """Fetch temperature using Open-Meteo API."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        r = requests.get(url, timeout=10)
        data = r.json()
        if "current_weather" in data:
            return round(data["current_weather"]["temperature"], 1)
        return 30
    except:
        st.warning("Couldn't fetch weather. Using default 30°C.")
        return 30


def set_goal_based_on_climate(temp):
    if temp >= 35:
        return 3500
    elif temp >= 30:
        return 3000
    elif temp >= 25:
        return 2500
    else:
        return 2000


def apply_theme_and_font(theme, font):
    """Apply custom theme and font style."""
    if theme == "Dark":
        st.markdown("""
        <style>
        .stApp {
            background-color: #121212;
            color: #f5f5f5;
        }
        div.stButton > button:first-child {
            background-color: #f5f5f5;
            color: #000000;
            border-radius: 10px;
            border: none;
            padding: 0.5em 1em;
        }
        div.stButton > button:first-child:hover {
            background-color: #dddddd;
            color: #000;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .stApp {
            background-color: #ffffff;
            color: #000000;
        }
        div.stButton > button:first-child {
            background-color: #2196F3;
            color: #ffffff;
            border-radius: 10px;
            border: none;
            padding: 0.5em 1em;
        }
        div.stButton > button:first-child:hover {
            background-color: #1976D2;
            color: #fff;
        }
        </style>
        """, unsafe_allow_html=True)

    font_sizes = {"Small": "14px", "Medium": "16px", "Large": "18px"}
    st.markdown(f"""
    <style>
    body, p, div, input, button, label {{
        font-size: {font_sizes.get(font, '16px')} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# =========================
# PAGE FUNCTIONS
# =========================

def login_page():
    st.title("💧 Water Buddy Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if not username or not password:
            st.warning("⚠️ Please enter both username and password.")
            return

        users = firebase_get("users")
        if users == {}:
            st.error("❌ No accounts found. Please sign up first.")
            return

        if username in users and users[username]["password"] == hash_password(password):
            st.session_state["user"] = username
            # keep behavior you had earlier (opening settings after login)
            st.session_state["page"] = "settings"
            st.success("✅ Login successful!")
            st.rerun()
        elif username not in users:
            st.error("❌ Username does not exist. Please sign up first.")
        else:
            st.error("❌ Incorrect password. Try again.")

    st.markdown("---")
    st.write("Don't have an account?")
    if st.button("Sign Up"):
        st.session_state["page"] = "signup"


def signup_page():
    st.title("🧊 Create Your Water Buddy Account")

    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")

    if st.button("Sign Up"):
        if not username or not password:
            st.warning("⚠️ Please enter both username and password.")
            return

        users = firebase_get("users")
        if users is None:
            users = {}

        if username in users:
            st.error("❌ Username already exists. Please choose another one.")
            return

        lat, lon = 13.0827, 80.2707
        default_city = "Chennai"

        try:
            headers = {"User-Agent": "WaterBuddyApp/1.0"}
            url = f"https://nominatim.openstreetmap.org/search?city={default_city}&format=json"
            r = requests.get(url, headers=headers, timeout=10)
            geo = r.json()
            if isinstance(geo, list) and len(geo) > 0:
                lat = float(geo[0]["lat"])
                lon = float(geo[0]["lon"])
        except:
            st.warning("⚠️ Location fetch failed, using Chennai defaults.")

        user_data = {
            "password": hash_password(password),
            "goal": 2000,
            "age": 18,
            "age_group": "None / Prefer climate-based",
            "logged": 0,
            "location": default_city,
            "lat": lat,
            "lon": lon,
            "theme": "Light",
            "font": "Medium",
            "last_reset": str(datetime.date.today()),
            "history": [],
            "rewards": 0,
            "completed_tasks": {},
        }

        firebase_patch(f"users/{username}", user_data)
        st.success("✅ Account created successfully! You can now log in.")
        st.session_state["page"] = "login"
        st.rerun()


def home_page():
    st.title("🏠 Water Buddy Home")

    username = st.session_state.get("user")
    if not username:
        st.error("⚠️ No user in session. Please log in.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    user_data = firebase_get(f"users/{username}")

    if not user_data:
        st.error("⚠️ User data not found. Please log in again.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    apply_theme_and_font(user_data.get("theme", "Light"), user_data.get("font", "Medium"))

    today = str(datetime.date.today())
    # Reset daily log if needed
    if user_data.get("last_reset") != today:
        user_data["logged"] = 0
        user_data["last_reset"] = today
        # reset daily completed tasks optionally:
        user_data["completed_tasks"] = {}
        firebase_patch(f"users/{username}", user_data)

    st.write("📍 Enter your city:")
    city = st.text_input("City", value=user_data.get("location", "Chennai"))

    if st.button("Update Location"):
        try:
            headers = {"User-Agent": "WaterBuddyApp/1.0"}
            url = f"https://nominatim.openstreetmap.org/search?city={city}&format=json"
            response = requests.get(url, headers=headers, timeout=10)
            geo = response.json()
            if isinstance(geo, list) and len(geo) > 0:
                lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
                user_data["location"], user_data["lat"], user_data["lon"] = city, lat, lon
                firebase_patch(f"users/{username}", user_data)
                st.success(f"✅ Location updated to {city}!")
            else:
                st.warning("⚠️ Couldn't fetch that city. Using default (Madurai).")
                user_data.update({"location": "Madurai", "lat": 9.9252, "lon": 78.1198})
                firebase_patch(f"users/{username}", user_data)
        except:
            st.warning("⚠️ Weather service not reachable. Using default (Madurai).")
            user_data.update({"location": "Madurai", "lat": 9.9252, "lon": 78.1198})
            firebase_patch(f"users/{username}", user_data)

    # Determine goal: prefer saved age_group goal; otherwise climate-based
    lat, lon = user_data.get("lat", 9.9252), user_data.get("lon", 78.1198)
    temp = get_weather_data(lat, lon)
    climate_goal = set_goal_based_on_climate(temp)

    stored_age_group = user_data.get("age_group")
    stored_goal = user_data.get("goal")

    if stored_age_group and stored_age_group != "None / Prefer climate-based":
        # Use stored goal (ensure exists in mapping)
        mapped = AGE_GROUP_GOALS_ML.get(stored_age_group)
        if mapped is not None:
            goal = mapped
        else:
            # fallback if mapping missing
            goal = stored_goal or climate_goal
    else:
        # No age group preference: use climate-based goal
        goal = climate_goal
        # update user's goal in firebase so UI shows consistent value
        user_data["goal"] = goal
        firebase_patch(f"users/{username}", {"goal": goal})

    # If stored goal differs from computed goal (and age_group is set), keep stored goal
    user_data["goal"] = goal
    firebase_patch(f"users/{username}", {"goal": goal})

    st.markdown(f"### 🌤️ {user_data.get('location', 'Unknown')}: {temp}°C")
    st.markdown(f"**🎯 Daily Goal:** {goal} ml")
    st.markdown(f"**💧 Logged So Far:** {user_data.get('logged', 0)} ml")
    st.write("🕒", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # progress bar
    progress = 0.0
    try:
        progress = min(user_data.get("logged", 0) / float(goal), 1.0)
    except Exception:
        progress = 0.0
    st.progress(progress)
    st.caption(f"{int(progress * 100)}% of your goal achieved!")

    # Plot 1: Bar
    fig, ax = plt.subplots(figsize=(5, 2.5))
    ax.bar(["Goal", "Logged"], [goal, user_data.get("logged", 0)],
           color=["#90CAF9", "#42A5F5"], width=0.5)
    ax.set_ylabel("ml")
    ax.set_title("Today's Hydration Progress")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    st.pyplot(fig)

    # Ensure history exists and update today's entry
    if "history" not in user_data:
        user_data["history"] = []

    if not user_data["history"] or user_data["history"][-1].get("date") != today:
        user_data["history"].append({"date": today, "logged": user_data.get("logged", 0)})
        if len(user_data["history"]) > 7:
            user_data["history"].pop(0)
        firebase_patch(f"users/{username}", {"history": user_data["history"]})

    # Weekly Trend
    st.subheader("📊 Weekly Hydration Trend")
    dates = [d["date"][-5:] for d in user_data.get("history", [])]
    logged = [d["logged"] for d in user_data.get("history", [])]

    if dates and logged:
        fig2, ax2 = plt.subplots(figsize=(5, 2.5))
        ax2.plot(dates, logged, marker="o")
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Water (ml)")
        ax2.set_title("Hydration Over the Last 7 Days")
        ax2.grid(alpha=0.4)
        st.pyplot(fig2)
    else:
        st.info("No history yet — log some water to see trends!")

    # If tasks were completed and pushed to session_state, show prompt to log
    if "tasks_to_log" in st.session_state and st.session_state["tasks_to_log"]:
        st.info("You completed tasks — log the recommended water from those tasks on Home.")
        st.write(st.session_state["tasks_to_log"])

    # Add water input
    add = st.number_input("Add water intake (ml):", min_value=0, step=50)
    if st.button("Log Water"):
        user_data["logged"] = user_data.get("logged", 0) + int(add)
        firebase_patch(f"users/{username}", {"logged": user_data["logged"]})
        if user_data["logged"] >= goal:
            st.balloons()
            st.success("🎉 Goal achieved! Stay hydrated 💦")
        st.rerun()

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Tasks 📋"):
            st.session_state["page"] = "tasks"
            st.rerun()
    with col2:
        if st.button("Settings ⚙️"):
            st.session_state["page"] = "settings"
            st.rerun()


def tasks_page():
    st.title("📋 Daily Hydration Tasks")

    username = st.session_state.get("user")
    if not username:
        st.warning("Please log in to view your tasks.")
        return

    user_data = firebase_get(f"users/{username}") or {}

    if "completed_tasks" not in user_data:
        user_data["completed_tasks"] = {}
    if "rewards" not in user_data:
        user_data["rewards"] = 0

    tasks = [
        {"id": "t1", "text": "Drink 1 cup of water now (200 ml)", "amount": 200},
        {"id": "t2", "text": "Drink water before your meal (250 ml)", "amount": 250},
        {"id": "t3", "text": "Refill your bottle (no log)", "amount": 0},
        {"id": "t4", "text": "Take 2 sips right now (100 ml)", "amount": 100},
    ]

    st.write("💧 Click a task to complete it and earn rewards!")

    if "tasks_to_log" not in st.session_state:
        st.session_state["tasks_to_log"] = []

    for t in tasks:
        key = f"task_{t['id']}"
        completed = user_data.get("completed_tasks", {}).get(key, False)

        if completed:
            st.success(f"✅ {t['text']} (Completed)")
        else:
            if st.button(t["text"], key=key):
                user_data.setdefault("completed_tasks", {})[key] = True
                user_data["rewards"] = user_data.get("rewards", 0) + 10

                firebase_patch(
                    f"users/{username}",
                    {
                        "completed_tasks": user_data["completed_tasks"],
                        "rewards": user_data["rewards"]
                    }
                )

                st.session_state["tasks_to_log"].append(t)
                st.success("🎉 Task completed! You earned +10 points!")
                st.session_state["page"] = "home"
                st.rerun()

    st.markdown("---")
    st.markdown(f"**🏆 Total Rewards:** {user_data.get('rewards', 0)} points")
    st.caption("Tasks reset each day when you reset your daily log.")

    st.divider()
    st.subheader("🚀 Navigation")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🏠 Go to Home"):
            st.session_state["page"] = "home"
            st.rerun()
    with col2:
        if st.button("⚙️ Settings"):
            st.session_state["page"] = "settings"
            st.rerun()
    with col3:
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.session_state["page"] = "login"
            st.rerun()


def settings_page():
    st.title("⚙️ Settings")

    username = st.session_state.get("user")
    if not username:
        st.error("⚠️ Please log in first.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    user_data = firebase_get(f"users/{username}") or {}

    apply_theme_and_font(user_data.get("theme", "Light"), user_data.get("font", "Medium"))

    st.subheader("🎨 Theme & Font")
    theme = st.radio("Choose Theme:", ["Light", "Dark"], index=0 if user_data.get("theme", "Light") == "Light" else 1)
    font = st.radio("Font Size:", ["Small", "Medium", "Large"],
                    index=["Small", "Medium", "Large"].index(user_data.get("font", "Medium")))

    if theme != user_data.get("theme") or font != user_data.get("font"):
        user_data["theme"], user_data["font"] = theme, font
        firebase_patch(f"users/{username}", {"theme": theme, "font": font})
        st.success("✅ Display settings updated!")
        st.rerun()

    st.divider()
    st.subheader("👤 Age Settings")
    # keep the numeric age input (optional)
    age = st.number_input("Enter your age:", min_value=0, max_value=120, value=int(user_data.get("age", 18)))
    if st.button("💾 Save Age"):
        user_data["age"] = int(age)
        firebase_patch(f"users/{username}", {"age": user_data["age"]})
        st.success("🎉 Age updated successfully!")

    st.divider()
    st.subheader("🧭 Age Group (select to auto-set goal)")

    # preselect current age group if present
    current_group = user_data.get("age_group", "None / Prefer climate-based")
    selected = st.selectbox("Choose your age group:", AGE_GROUP_OPTIONS, index=AGE_GROUP_OPTIONS.index(current_group) if current_group in AGE_GROUP_OPTIONS else AGE_GROUP_OPTIONS.index("None / Prefer climate-based"))

    if st.button("Set Age Group & Update Goal"):
        # map selection to goal
        mapped_goal = AGE_GROUP_GOALS_ML.get(selected)
        # If user chooses 'None / Prefer climate-based', we will compute time-of-day/climate goal on home page
        if mapped_goal is None:
            # Remove age_group preference and let climate decide
            firebase_patch(f"users/{username}", {"age_group": "None / Prefer climate-based"})
            st.success("✅ Age group preference cleared — app will use climate-based goal.")
        else:
            # Save both age_group and goal (in mL)
            firebase_patch(f"users/{username}", {"age_group": selected, "goal": mapped_goal})
            st.success(f"✅ Age group set to '{selected}' and daily goal updated to {mapped_goal} ml.")
        st.rerun()

    st.divider()
    st.subheader("💧 Water Log Controls")
    if st.button("🔁 Reset Daily Water Log"):
        firebase_patch(f"users/{username}", {"logged": 0})
        st.success("Water log reset for today!")
        st.rerun()

    st.divider()
    st.subheader("🧩 Reset All Settings")
    if st.button("♻️ Reset to Default Settings"):
        defaults = {
            "theme": "Light",
            "font": "Medium",
            "goal": 2000,
            "logged": 0,
            "location": "Chennai",
            "lat": 13.0827,
            "lon": 80.2707,
            "age": 18,
            "age_group": "None / Prefer climate-based",
            "completed_tasks": {},
            "rewards": 0
        }
        firebase_patch(f"users/{username}", defaults)
        st.success("✅ Settings reset to default.")
        st.rerun()

    st.divider()
    st.subheader("🚀 Navigation")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🏠 Go to Home"):
            st.session_state["page"] = "home"
            st.rerun()
    with col2:
        if st.button("📋 Go to Tasks"):
            st.session_state["page"] = "tasks"
            st.rerun()
    with col3:
        if st.button("🚪 Logout"):
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

