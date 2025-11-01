##EMAIL_ADDRESS = "sarveshtamilgaming2010@gmail.com"
##EMAIL_PASSWORD = "znna ksnu ycxa sabu"

import streamlit as st
import json, os, random, datetime
import geocoder
from streamlit_autorefresh import st_autorefresh

DATA_FILE = "users_data.json"

# ------------------- Utility Functions -------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_weather():
    try:
        g = geocoder.ip('me')
        city = g.city or "Unknown"
        temp = random.randint(25, 35)
        cond = random.choice(["☀️ Sunny", "🌦️ Rainy", "🌤️ Cloudy"])
        return city, cond, temp
    except:
        return "Unknown", "❓ Unknown", "-"

def send_notification():
    st.toast("💧 Time to drink some water!")

def apply_theme(user):
    font = user.get("font_size", "16px")
    theme = user.get("theme", "Light")
    bg = "#121212" if theme == "Dark" else "#f0f0f0"
    text = "white" if theme == "Dark" else "black"
    st.markdown(f"""
    <style>
    html, body, [class*="css"]  {{
        background-color: {bg} !important;
        color: {text} !important;
        font-size: {font};
    }}
    </style>
    """, unsafe_allow_html=True)

# ------------------- Login / Sign Up -------------------
def login_signup_page():
    st.title("💧 Water Hydrator Login / Sign Up")
    users = load_data()
    option = st.radio("Choose an option", ["Login", "Sign Up"], horizontal=True)

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if option == "Sign Up":
        name = st.text_input("Your Name")
        age = st.number_input("Age", min_value=1, max_value=120, step=1)

        if st.button("Create Account"):
            if email in users:
                st.error("⚠️ Account already exists.")
            elif not name or not password:
                st.warning("Please fill all fields.")
            else:
                users[email] = {
                    "password": password,
                    "name": name,
                    "age": age,
                    "goal": 2000,
                    "intake": 0,
                    "font_size": "16px",
                    "theme": "Light",
                    "mascot": "🐬",
                    "health_issue": "",
                    "tasks_state": {}
                }
                save_data(users)
                st.success("✅ Account created successfully!")
                # Auto login after signup
                st.session_state.user = email
                st.session_state.page = "Dashboard"
                #st.experimental_rerun()

    else:
        if st.button("Login"):
            if email in users and users[email]["password"] == password:
                st.session_state.user = email
                st.session_state.page = "Dashboard"
                #st.experimental_rerun()
            else:
                st.error("❌ Invalid credentials.")

# ------------------- Dashboard -------------------
def dashboard():
    user_data = load_data()
    user = user_data[st.session_state.user]
    apply_theme(user)

    st.title("💧 Water Hydrator Dashboard")
    st.write(f"Welcome, **{user['name']}** 👋")
    st.write("🕒", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    city, cond, temp = get_weather()
    st.write(f"🌍 Location: {city}")
    st.write(f"{cond}, {temp}°C")

    goal = user.get("goal", 2000)
    st.subheader(f"Your daily goal: {goal} ml")

    amount = st.number_input("Enter water intake (ml)", min_value=0, step=50)
    if st.button("Log Intake"):
        user["intake"] += amount
        save_data(user_data)
        st.success(f"💧 Added {amount} ml! Total today: {user['intake']} ml")

    st.progress(min(user["intake"] / goal, 1.0))
    if user["intake"] >= goal:
        st.balloons()
        st.success("🎉 Goal reached! Stay hydrated!")

    st_autorefresh(interval=1000 * 60 * 60, key="notifier")  # every hour
    if random.random() < 0.05:
        send_notification()

# ------------------- Tasks -------------------
def tasks_page():
    st.title("✅ Daily Tasks")
    users = load_data()
    user = users[st.session_state.user]
    tasks = [
        "Drink 500 ml water",
        "Drink 1 litre water",
        "Complete daily goal"
    ]

    # Make sure tasks_state exists for the user
    if "tasks_state" not in user:
        user["tasks_state"] = {}

    for task in tasks:
        try:
            completed = user["tasks_state"].get(task, False)
        except Exception:
            completed = False  # if something goes wrong, assume not completed

        if completed:
            st.success(f"✅ {task} — Completed!")
        else:
            if st.button(f"Mark '{task}' Complete", key=task):
                try:
                    user["tasks_state"][task] = True
                    save_data(users)
                    st.success(f"🎉 {task} marked as complete!")
                    st.session_state.page = "Dashboard"
                    st.rerun()
                except Exception:
                    pass  # silently ignore one-time write errors

# ------------------- Settings -------------------
def settings_page():
    st.title("⚙️ Settings")
    users = load_data()
    user = users[st.session_state.user]

    font_size = st.selectbox("Font Size", ["14px", "16px", "18px", "20px"], index=["14px", "16px", "18px", "20px"].index(user["font_size"]))
    theme = st.selectbox("Theme", ["Light", "Dark"], index=["Light", "Dark"].index(user["theme"]))
    age = st.number_input("Age", min_value=1, max_value=120, value=user["age"])
    mascot = st.selectbox("Mascot", ["🐬 Dolphin", "🐟 Fish", "🤖 Robot", "🐢 Tortoise", "💧 Water Drop"])
    health = st.text_input("Health Issues (optional)", user.get("health_issue", ""))

    if st.button("💾 Save Settings"):
        user["font_size"] = font_size
        user["theme"] = theme
        user["age"] = age
        user["mascot"] = mascot.split()[0]
        user["health_issue"] = health
        save_data(users)
        st.success("✅ Settings saved successfully!")

    if st.button("🔄 Reset App Data"):
        user["intake"] = 0
        user["tasks_state"] = {}
        save_data(users)
        st.success("🔁 App data reset!")

# ------------------- Main -------------------
def main():
    st.set_page_config(page_title="💧 Water Hydrator", page_icon="💧")

    if "page" not in st.session_state:
        st.session_state.page = "Login"

    if "user" not in st.session_state:
        login_signup_page()
    else:
        if st.session_state.page == "Dashboard":
            dashboard()
        elif st.session_state.page == "Tasks":
            tasks_page()
        elif st.session_state.page == "Settings":
            settings_page()

    # Sidebar navigation
    if "user" in st.session_state:
        st.sidebar.title("📂 Navigation")
        if st.sidebar.button("🏠 Dashboard"):
            st.session_state.page = "Dashboard"
        if st.sidebar.button("✅ Tasks"):
            st.session_state.page = "Tasks"
        if st.sidebar.button("⚙️ Settings"):
            st.session_state.page = "Settings"
        if st.sidebar.button("🚪 Logout"):
            st.session_state.clear()
            st.experimental_rerun()

if __name__ == "__main__":
    main()

