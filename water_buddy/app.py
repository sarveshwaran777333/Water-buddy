import streamlit as st
import requests
import datetime
import matplotlib.pyplot as plt
import matplotlib as mpl
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
    "Older adults (65+)": 3500,
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


def _get_theme_styles(theme, font):
    """Return (text_color, background_css, button_bg, button_text) for theme."""
    font_sizes = {"Small": "14px", "Medium": "16px", "Large": "18px"}
    fs = font_sizes.get(font, "16px")

    if theme == "Dark":
        text_color = "#ffffff"              # pure white
        page_bg = "#0f1720"                # deep dark
        accent = "#00bcd4"                 # aqua-ish for small accents if needed
        button_bg = "#ffffff"              # buttons white in dark mode
        button_text = "#000000"            # black text on white buttons
    elif theme == "Aqua":
        text_color = "#002b5c"             # dark blue text
        page_bg = "linear-gradient(135deg, #e6fbff 0%, #d0f7ff 100%)"  # soft aqua bg
        accent = "#0288d1"
        button_bg = "#8a2be2"              # purple buttons
        button_text = "#ffffff"
    else:  # Light (default)
        text_color = "#000000"
        page_bg = "#ffffff"
        accent = "#2196F3"
        button_bg = "#2196F3"
        button_text = "#ffffff"

    # A broad CSS that targets many Streamlit elements. Streamlit's internal classes vary,
    # so we use broad selectors (body, div, label, .stMarkdown, input, select, textarea, etc.).
    css = f"""
    <style>
    /* Page background */
    .stApp {{
        background: {page_bg} !important;
    }}

    /* Global text */
    body, .stApp, .css-1d391kg, .css-1lcbmhc, .stMarkdown, p, label, span, div, h1, h2, h3, h4, h5, h6 {{
        color: {text_color} !important;
        font-size: {fs} !important;
    }}

    /* Headings */
    h1, h2, h3, h4, h5, h6 {{
        color: {text_color} !important;
    }}

    /* Buttons */
    div.stButton > button:first-child {{
        background-color: {button_bg} !important;
        color: {button_text} !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.5em 1em !important;
        box-shadow: none !important;
    }}
    div.stButton > button:first-child:hover {{
        opacity: 0.95;
        transform: translateY(-1px);
    }}

    /* Inputs, selects, textareas */
    input, textarea, select {{
        color: {text_color} !important;
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(0,0,0,0.08) !important;
    }}

    /* Streamlit labels & widget text */
    .stTextInput label, .stNumberInput label, label {{
        color: {text_color} !important;
    }}

    /* Radio / Selectbox / Checkbox text */
    .stRadio, .stSelectbox, .stCheckbox, .stMultiSelect {{
        color: {text_color} !important;
    }}

    /* Sidebar (if used) */
    .css-1lcbmhc .stApp {{
        color: {text_color} !important;
    }}

    /* Captions and small text */
    .stCaption, .css-4rbku5, .css-1avcm0n {{
        color: {text_color} !important;
    }}

    /* Links */
    a {{
        color: {accent} !important;
    }}

    /* Make placeholder text slightly muted but matching theme */
    ::placeholder {{
        color: {text_color} !important;
        opacity: 0.6;
    }}

    /* Ensure widget icons adjust (if any) */
    svg {{
        fill: {text_color} !important;
    }}
    </style>
    """
    return text_color, css, button_bg, button_text


def apply_theme_and_font(theme: str, font: str):
    """
    Apply custom CSS for the chosen theme and adjust matplotlib colors.
    Call this at the top of every page render so matplotlib and the page are consistent.
    """
    text_color, css, button_bg, button_text = _get_theme_styles(theme, font)
    st.markdown(css, unsafe_allow_html=True)

    # Update matplotlib colors so charts match the theme
    mpl.rcParams.update({
        'text.color': text_color,
        'axes.labelcolor': text_color,
        'xtick.color': text_color,
        'ytick.color': text_color,
        'axes.facecolor': "none",  # keep transparent so it inherits page bg
        'figure.facecolor': "none",
    })


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

        if username in users and users[username].get("password") == hash_password(password):
            st.session_state["user"] = username
            st.session_state["page"] = "home"
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

        # Defaults
        user_data = {
            "password": hash_password(password),
            "goal": AGE_GROUP_GOALS_ML["age 19-50"],
            "age": 18,
            "age_group": "age 19-50",
            "logged": 0,
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

    # Apply user's chosen theme/font (default to Light/Medium)
    apply_theme_and_font(user_data.get("theme", "Light"), user_data.get("font", "Medium"))

    today = str(datetime.date.today())
    # Reset daily log if needed
    if user_data.get("last_reset") != today:
        user_data["logged"] = 0
        user_data["last_reset"] = today
        user_data["completed_tasks"] = {}
        firebase_patch(f"users/{username}", user_data)

    # Determine goal: use age_group mapping only
    selected_group = user_data.get("age_group")
    if selected_group in AGE_GROUP_GOALS_ML:
        goal = AGE_GROUP_GOALS_ML[selected_group]
    else:
        goal = user_data.get("goal", AGE_GROUP_GOALS_ML["age 19-50"])

    # Save cleaned goal
    user_data["goal"] = goal
    firebase_patch(f"users/{username}", {"goal": goal})

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
    ax.bar(["Goal", "Logged"], [goal, user_data.get("logged", 0)], width=0.5)
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

    # Theme & Font controls will be saved to user profile.
    st.subheader("🎨 Theme & Font")

    # Load stored theme (default Light) and font (default Medium)
    stored_theme = user_data.get("theme", "Light")
    stored_font = user_data.get("font", "Medium")

    theme = st.radio("Choose Theme:", ["Light", "Dark", "Aqua"],
                     index=["Light", "Dark", "Aqua"].index(stored_theme) if stored_theme in ["Light", "Dark", "Aqua"] else 0)
    font = st.radio("Font Size:", ["Small", "Medium", "Large"],
                    index=["Small", "Medium", "Large"].index(stored_font) if stored_font in ["Small", "Medium", "Large"] else 1)

    # Apply immediately so user sees the effect on the same page
    apply_theme_and_font(theme, font)

    if (theme != stored_theme) or (font != stored_font):
        if st.button("💾 Save Display Settings"):
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
    st.subheader("🧭 Age Group & Custom Water Goal")

    # Load saved age group and goal
    current_group = user_data.get("age_group", AGE_GROUP_OPTIONS[0])
    saved_goal = int(user_data.get("goal", AGE_GROUP_GOALS_ML.get(current_group, AGE_GROUP_GOALS_ML["age 19-50"])))

    # Age group selectbox
    selected_group = st.selectbox(
        "Choose your age group:",
        AGE_GROUP_OPTIONS,
        index=AGE_GROUP_OPTIONS.index(current_group) if current_group in AGE_GROUP_OPTIONS else 0
    )

    # Default goal based on selected group
    default_goal = AGE_GROUP_GOALS_ML.get(selected_group, saved_goal)

    # Editable goal box
    custom_goal = st.number_input(
        "Standard Water Goal (mL) — you can edit this",
        value=int(default_goal),
        step=100
    )

    # Save both group + goal
    if st.button("💾 Save Age Group & Goal"):
        firebase_patch(f"users/{username}", {
            "age_group": selected_group,
            "goal": int(custom_goal)
        })
        st.success(f"Saved! Age group set to '{selected_group}', daily goal = {custom_goal} mL.")
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
            "goal": AGE_GROUP_GOALS_ML["age 19-50"],
            "logged": 0,
            "age": 18,
            "age_group": "age 19-50",
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
