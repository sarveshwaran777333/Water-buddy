import streamlit as st
import requests
import datetime
import matplotlib.pyplot as plt
import json
import urllib.request

FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"


def firebase_get(path):
    url = f"{FIREBASE_URL}{path}.json"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception:
        return None


def firebase_patch(path, data):
    url = f"{FIREBASE_URL}{path}.json"
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method="PATCH")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None


def firebase_put(path, data):
    url = f"{FIREBASE_URL}{path}.json"
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method="PUT")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None


# ---------------------------
# 💧 Water Goal Recommendation
# ---------------------------
def recommended_goal(age, gender="Not specified"):
    if age <= 0.5:
        return 700
    elif age <= 1:
        return 800
    elif age <= 3:
        return 1300
    elif age <= 8:
        return 1700
    elif age <= 13:
        return 2400 if gender.lower() in ["male", "boy"] else 2100
    elif age <= 18:
        return 3300 if gender.lower() in ["male", "boy"] else 2300
    elif age <= 64:
        return 3700 if gender.lower() in ["male", "man"] else 2700
    else:
        return 2300


# ---------------------------
# 🔐 Signup Page
# ---------------------------
def signup_page():
    st.title("🧍‍♀️ Create Your Water Buddy Account")

    username = st.text_input("Enter Username")
    password = st.text_input("Enter Password", type="password")
    age = st.number_input("Enter your age:", min_value=1, max_value=100, value=18)
    daily_goal = recommended_goal(age)

    default_city = "Chennai"
    try:
        geo = requests.get(
            f"https://nominatim.openstreetmap.org/search?city={default_city}&format=json",
            headers={"User-Agent": "WaterBuddyApp"},
            timeout=5
        )
        location_data = geo.json()
        lat, lon = (location_data[0]["lat"], location_data[0]["lon"]) if location_data else (0, 0)
    except Exception:
        lat, lon = 0, 0

    if st.button("Sign Up"):
        if username and password:
            user_data = {
                "password": password,
                "created_at": str(datetime.date.today()),
                "age": age,
                "daily_goal": daily_goal,
                "rewards": 0,
                "completed_tasks": {},
                "logged_today": 0,
                "history": {},
                "location": {"lat": lat, "lon": lon}
            }
            firebase_put(f"users/{username}", user_data)
            st.success("✅ Account created successfully! You can log in now.")
            st.session_state["page"] = "login"
            st.rerun()
        else:
            st.warning("Please fill all fields.")


# ---------------------------
# 🔓 Login Page
# ---------------------------
def login_page():
    st.title("🔐 Login to Water Buddy")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user_data = firebase_get(f"users/{username}")
        if user_data and user_data.get("password") == password:
            st.session_state["user"] = username
            st.session_state["page"] = "home"
            st.session_state["daily_goal"] = user_data.get("daily_goal", 2000)
            st.session_state["age"] = user_data.get("age", 18)
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid username or password.")


# ---------------------------
# 🏠 Home Page
# ---------------------------
def home_page():
    st.title("🏠 Water Buddy Home")

    username = st.session_state.get("user")
    if not username:
        st.warning("Please log in first.")
        return

    user_data = firebase_get(f"users/{username}") or {}
    daily_goal = user_data.get("daily_goal", 2000)
    logged_today = user_data.get("logged_today", 0)
    today_str = str(datetime.date.today())

    st.metric("Today's Water Intake", f"{logged_today} ml", f"Goal: {daily_goal} ml")

    add_ml = st.number_input("💧 Log Water Intake (ml)", min_value=50, max_value=2000, step=50)
    if st.button("Log Water"):
        new_total = logged_today + add_ml

        # Update today's log and history
        history = user_data.get("history", {})
        history[today_str] = new_total

        firebase_patch(f"users/{username}", {"logged_today": new_total, "history": history})
        st.success(f"Logged {add_ml} ml! Total: {new_total} ml")
        st.rerun()

    progress = min(logged_today / daily_goal, 1)
    st.progress(progress)
    if progress >= 1:
        st.balloons()

    # 📊 Hydration History Chart
    st.markdown("---")
    st.subheader("📈 Your Hydration Progress")

    history = user_data.get("history", {})
    if history:
        dates = list(history.keys())[-7:]  # last 7 days
        values = [history[d] for d in dates]
        goals = [daily_goal for _ in dates]

        plt.figure(figsize=(6, 3))
        plt.plot(dates, values, marker="o", label="Actual Intake (ml)")
        plt.plot(dates, goals, linestyle="--", label="Goal (ml)")
        plt.xticks(rotation=30)
        plt.ylabel("Water (ml)")
        plt.legend()
        st.pyplot(plt)
    else:
        st.info("No history yet. Start logging to see your progress!")

    # 🚀 Navigation
    st.markdown("---")
    st.subheader("🚀 Navigation")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📋 Tasks"):
            st.session_state["page"] = "tasks"
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


# ---------------------------
# 📋 Tasks Page
# ---------------------------
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
                firebase_patch(f"users/{username}", {
                    "completed_tasks": user_data["completed_tasks"],
                    "rewards": user_data["rewards"]
                })

                st.session_state["tasks_to_log"].append(t)
                st.success("🎉 Task completed! You earned +10 points!")
                st.session_state["page"] = "home"
                st.rerun()

    st.markdown("---")
    st.markdown(f"**🏆 Total Rewards:** {user_data.get('rewards', 0)} points")

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


# ---------------------------
# ⚙️ Settings Page
# ---------------------------
def settings_page():
    st.title("⚙️ Settings")

    username = st.session_state.get("user")
    if not username:
        st.warning("Please log in first.")
        return

    user_data = firebase_get(f"users/{username}") or {}
    current_age = user_data.get("age", 18)
    current_goal = user_data.get("daily_goal", recommended_goal(current_age))

    st.subheader("👶 Personal Info")
    age = st.number_input("Age:", min_value=1, max_value=100, value=current_age)

    auto_goal = recommended_goal(age)
    st.info(f"💧 Recommended daily goal for age {age}: **{auto_goal} ml**")

    st.subheader("🎯 Custom Daily Goal")
    daily_goal = st.number_input(
        "Set your preferred daily water goal (ml):",
        min_value=500,
        max_value=6000,
        value=int(current_goal)
    )

    if st.button("💾 Save Settings"):
        firebase_patch(f"users/{username}", {"age": age, "daily_goal": daily_goal})
        st.success("✅ Settings updated successfully!")
        st.session_state["daily_goal"] = daily_goal
        st.session_state["age"] = age

    st.markdown("---")
    st.subheader("🚀 Navigation")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🏠 Home"):
            st.session_state["page"] = "home"
            st.rerun()
    with col2:
        if st.button("📋 Tasks"):
            st.session_state["page"] = "tasks"
            st.rerun()
    with col3:
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.session_state["page"] = "login"
            st.rerun()


# ---------------------------
# 🧭 Page Router
# ---------------------------
if "page" not in st.session_state:
    st.session_state["page"] = "login"

page = st.session_state["page"]

if page == "login":
    login_page()
elif page == "signup":
    signup_page()
elif page == "home":
    home_page()
elif page == "tasks":
    tasks_page()
elif page == "settings":
    settings_page()
