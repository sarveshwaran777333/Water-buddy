import streamlit as st
import requests
import hashlib
import datetime
import random
from typing import Any, Dict, Optional

# -----------------------
# CONFIG - update if needed
# -----------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app/"  # MUST end with '/'
REQUEST_TIMEOUT = 6  # seconds

AGE_GROUP_GOALS = {
    "6-12": 1600,
    "13-18": 2000,
    "19-50": 2500,
    "51-64": 2400,
    "65+": 2200
}
QUICK_LOG_ML = 250
CUP_ML = 240

RANDOM_TIPS = [
    "Start your day with a glass of water.",
    "Carry a water bottle and sip often.",
    "Drink a small glass 20-30 minutes before meals.",
    "Add fruit slices for flavor—natural motivation!",
    "Sipping regularly beats chugging later."
]


# -----------------------
# Firebase helpers
# -----------------------
def firebase_get(path: str) -> Optional[Any]:
    try:
        url = FIREBASE_URL + path + ".json"
        res = requests.get(url, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        return res.json()
    except Exception:
        # Friendly message; avoid leaking internals
        st.error("Unable to reach Firebase. Check FIREBASE_URL and network.")
        return None


def firebase_put(path: str, payload: Any) -> Optional[Any]:
    try:
        url = FIREBASE_URL + path + ".json"
        res = requests.put(url, json=payload, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        return res.json()
    except Exception:
        st.error("Failed to write to Firebase.")
        return None


def firebase_patch(path: str, payload: Any) -> Optional[Any]:
    try:
        url = FIREBASE_URL + path + ".json"
        res = requests.patch(url, json=payload, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        return res.json()
    except Exception:
        st.error("Failed to update Firebase.")
        return None


# -----------------------
# Utilities
# -----------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ml_to_cups(ml: int) -> float:
    return ml / CUP_ML


def cups_to_ml(cups: float) -> int:
    return int(round(cups * CUP_ML))


def percent_of_goal(intake_ml: int, goal_ml: int) -> float:
    if goal_ml <= 0:
        return 0.0
    return min(100.0, (intake_ml / goal_ml) * 100.0)


def mascot_message(percent: float, intake_ml: int) -> str:
    if percent >= 100:
        return "🎉 Amazing — goal reached! Mascot dances."
    if percent >= 75:
        return "👏 So close — keep sipping!"
    if percent >= 50:
        return "👍 Halfway there — nice!"
    if percent >= 25:
        return "🙂 Good start — steady sips."
    if intake_ml == 0:
        return "👋 Let's begin — try a 250 ml sip."
    return "💧 Keep going — every sip counts."


def bottle_html(progress_pct: float, theme: str = "light") -> str:
    p = max(0, min(100, progress_pct))
    if theme == "dark":
        border = "#58a6ff"
        fill = "#0ea5e9"
        bg = "#071124"
        text = "#dbeafe"
    else:
        border = "#1f77b4"
        fill = "#1e90ff"
        bg = "#f7fdff"
        text = "#0f172a"
    html = f"""
    <div style="width:150px; margin: 8px auto; background:{bg}; padding:8px; border-radius:12px;">
      <div style="border:4px solid {border}; border-radius:24px; height:320px; width:75px; margin:0 auto; position:relative; overflow:hidden; background:linear-gradient(#fff,#eef);">
        <div style="position:absolute; bottom:0; left:0; width:100%; height:{p}%; background:{fill}; transition: height 0.6s ease-in-out; opacity:0.95;"></div>
      </div>
      <div style="text-align:center; font-size:13px; color:{text}; margin-top:6px;">Bottle: {p:.0f}%</div>
    </div>
    """
    return html


# -----------------------
# Session init
# -----------------------
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    if "water_data" not in st.session_state:
        st.session_state.water_data = {
            "date": str(datetime.date.today()),
            "age_group": "19-50",
            "standard_goal": AGE_GROUP_GOALS["19-50"],
            "user_goal": AGE_GROUP_GOALS["19-50"],
            "intake_ml": 0,
            "logs": [],
            "milestones_announced": []
        }
    # conv fields for converter
    if "conv_cups" not in st.session_state:
        st.session_state.conv_cups = 0.0
    if "conv_ml" not in st.session_state:
        st.session_state.conv_ml = 0


# -----------------------
# Data helpers
# -----------------------
def load_user_data(username: str) -> Dict[str, Any]:
    data = firebase_get(f"data/{username}") or {}
    # ensure defaults
    data.setdefault("date", str(datetime.date.today()))
    data.setdefault("age_group", "19-50")
    data.setdefault("standard_goal", AGE_GROUP_GOALS.get(data.get("age_group", "19-50"), AGE_GROUP_GOALS["19-50"]))
    data.setdefault("user_goal", data.get("user_goal", data["standard_goal"]))
    data.setdefault("intake_ml", 0)
    data.setdefault("logs", [])
    data.setdefault("milestones_announced", [])
    return data


def save_user_data(username: str, data: Dict[str, Any]) -> None:
    firebase_put(f"data/{username}", data)


def add_log(data: Dict[str, Any], amount: int, note: str = ""):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["intake_ml"] = int(data.get("intake_ml", 0)) + int(amount)
    logs = data.get("logs", [])
    logs.append({"time": now, "amount": int(amount), "note": note})
    data["logs"] = logs


# -----------------------
# Styling
# -----------------------
def apply_theme_styles():
    if st.session_state.theme == "dark":
        st.markdown(
            """
            <style>
            .stApp { background-color: #071124; color: #e6f2ff; }
            .css-1d391kg { color: #e6f2ff; }
            </style>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <style>
            .stApp { background-color: #ffffff; color: #0f172a; }
            </style>
            """,
            unsafe_allow_html=True
        )


# -----------------------
# Pages
# -----------------------
def login_page():
    apply_theme_styles()
    st.title("🔐 Login — WaterBuddy")
    st.write("Sign in to continue.")

    u = st.text_input("Username", key="login_user")
    p = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        if not u or not p:
            st.error("Enter both username and password.")
            return
        users = firebase_get("users") or {}
        if u not in users:
            st.error("User not found. Please signup.")
            return
        stored = users[u]
        # stored may be dict or plain string depending on how written; handle both
        stored_hash = stored.get("password") if isinstance(stored, dict) else stored
        if stored_hash == hash_password(p):
            st.success("Login successful — opening Settings.")
            st.session_state.logged_in = True
            st.session_state.user = u
            st.session_state.water_data = load_user_data(u)
            st.session_state.page = "settings"  # open settings directly
            st.rerun()
        else:
            st.error("Incorrect password.")


def signup_page():
    apply_theme_styles()
    st.title("🆕 Signup — WaterBuddy")
    st.write("Create a new account.")

    u = st.text_input("Choose username", key="signup_user")
    p = st.text_input("Choose password", type="password", key="signup_pass")

    if st.button("Create account"):
        if not u or not p:
            st.error("Please fill both fields.")
            return
        users = firebase_get("users") or {}
        if u in users:
            st.error("Username exists. Choose another.")
            return
        hashed = hash_password(p)
        res = firebase_put(f"users/{u}", {"password": hashed})
        if res is not None:
            # initialize per-user data
            default_data = {
                "date": str(datetime.date.today()),
                "age_group": "19-50",
                "standard_goal": AGE_GROUP_GOALS["19-50"],
                "user_goal": AGE_GROUP_GOALS["19-50"],
                "intake_ml": 0,
                "logs": [],
                "milestones_announced": []
            }
            firebase_put(f"data/{u}", default_data)
            st.success("Account created. Please login.")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("Failed to create account.")


def settings_page():
    apply_theme_styles()
    st.title("⚙ Settings")
    st.write(f"Hello, **{st.session_state.user}** — change settings below.")

    st.subheader("Theme")
    theme = st.radio("Choose theme", ["light", "dark"], index=0 if st.session_state.theme == "light" else 1)
    if theme != st.session_state.theme:
        st.session_state.theme = theme
        st.rerun()

    st.subheader("Water Goal (manual)")
    data = st.session_state.water_data
    age = data.get("age_group", "19-50")
    standard = AGE_GROUP_GOALS.get(age, AGE_GROUP_GOALS["19-50"])
    st.write(f"Standard for {age}: **{standard} ml**")
    new_goal = st.number_input("Set your daily goal (ml)", min_value=500, max_value=10000,
                               value=int(data.get("user_goal", standard)), step=50, key="settings_goal")
    if st.button("Save Goal"):
        data["user_goal"] = int(new_goal)
        save_user_data(st.session_state.user, data)
        st.success("Saved goal.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Home"):
            st.session_state.page = "home"
            st.rerun()
    with col2:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.page = "login"
            st.success("Logged out.")
            st.rerun()


def home_page():
    apply_theme_styles()
    st.title("💧 WaterBuddy — Home")
    st.write("Track your daily water. Data saved to your account.")

    data = st.session_state.water_data
    today = str(datetime.date.today())
    # Reset at new day
    if data.get("date") != today:
        data["date"] = today
        data["intake_ml"] = 0
        data["logs"] = []
        data["milestones_announced"] = []
        save_user_data(st.session_state.user, data)

    # Age and goal
    age = st.selectbox("Select your age group", options=list(AGE_GROUP_GOALS.keys()),
                       index=list(AGE_GROUP_GOALS.keys()).index(data.get("age_group", "19-50")))
    data["age_group"] = age
    data["standard_goal"] = AGE_GROUP_GOALS[age]
    st.write(f"Suggested: **{data['standard_goal']} ml**")
    user_goal = st.number_input("Your daily goal (ml)", min_value=500, max_value=10000,
                                value=int(data.get("user_goal", data["standard_goal"])), step=50, key="home_goal")
    data["user_goal"] = int(user_goal)

    st.markdown("---")
    col_q, col_c = st.columns([1, 2])
    with col_q:
        if st.button(f"+{QUICK_LOG_ML} ml"):
            add_log(data, QUICK_LOG_ML, note="quick")
            save_user_data(st.session_state.user, data)
            st.success(f"Added {QUICK_LOG_ML} ml")
            st.rerun()
    with col_c:
        custom_amt = st.number_input("Custom amount (ml)", min_value=10, max_value=5000, value=250, step=10, key="custom_amt")
        custom_note = st.text_input("Note (optional)", key="custom_note")
        if st.button("Add custom amount"):
            add_log(data, int(custom_amt), note=custom_note)
            save_user_data(st.session_state.user, data)
            st.success(f"Added {int(custom_amt)} ml")
            st.rerun()

    if st.button("Reset / Start New Day"):
        data["date"] = today
        data["intake_ml"] = 0
        data["logs"] = []
        data["milestones_announced"] = []
        save_user_data(st.session_state.user, data)
        st.success("Reset done.")
        st.rerun()

    st.markdown("---")
    # Calculations & visuals
    intake = int(data.get("intake_ml", 0))
    goal = int(data.get("user_goal", data["standard_goal"]))
    remaining = max(0, goal - intake)
    pct = percent_of_goal(intake, goal)

    left, right = st.columns([2, 1])
    with left:
        st.metric("So far (ml)", f"{intake} ml")
        st.metric("Remaining (ml)", f"{remaining} ml")
        st.metric("Progress", f"{pct:.0f}%")
        st.progress(int(pct))
        st.write(mascot_message(pct, intake))
        # announce milestones once
        for m in (25, 50, 75, 100):
            if pct >= m and m not in data.get("milestones_announced", []):
                data.setdefault("milestones_announced", []).append(m)
                save_user_data(st.session_state.user, data)
                if m == 100:
                    st.balloons()
                else:
                    st.success(f"Milestone: {m}%")
    with right:
        st.markdown(bottle_html(pct, theme=st.session_state.theme), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Today's logs")
    if data.get("logs"):
        for e in reversed(data["logs"]):
            note_str = f" — {e.get('note')}" if e.get("note") else ""
            st.write(f"{e.get('time')}: +{e.get('amount')} ml{note_str}")
    else:
        st.info("No logs yet — use +250 ml!")

    st.markdown("---")
    st.subheader("Unit converter")
    ccol, mcol = st.columns(2)
    with ccol:
        st.session_state.conv_cups = st.number_input("Cups", min_value=0.0, step=0.25, value=st.session_state.conv_cups, key="conv_cups_input")
    with mcol:
        st.session_state.conv_ml = st.number_input("ML", min_value=0, step=10, value=st.session_state.conv_ml, key="conv_ml_input")
    if st.button("Cups → ML"):
        st.session_state.conv_ml = cups_to_ml(st.session_state.conv_cups)
        st.rerun()
    if st.button("ML → Cups"):
        st.session_state.conv_cups = round(ml_to_cups(st.session_state.conv_ml), 2)
        st.rerun()

    st.markdown("---")
    st.info("Tip: " + random.choice(RANDOM_TIPS))
    # Persist at end
    save_user_data(st.session_state.user, data)


# -----------------------
# Page controller
# -----------------------
def main():
    init_session()

    # If logged in and water_data looks empty, attempt load
    if st.session_state.logged_in and (not st.session_state.water_data or st.session_state.water_data.get("date") is None):
        st.session_state.water_data = load_user_data(st.session_state.user)

    # route pages
    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "signup":
        signup_page()
    elif st.session_state.page == "settings":
        # require logged in for settings/home
        if not st.session_state.logged_in:
            st.warning("Please login first.")
            st.session_state.page = "login"
            st.rerun()
        settings_page()
    elif st.session_state.page == "home":
        if not st.session_state.logged_in:
            st.warning("Please login first.")
            st.session_state.page = "login"
            st.rerun()
        home_page()
    else:
        # fallback to login
        st.session_state.page = "login"
        st.rerun()


if __name__ == "__main__":
    main()
