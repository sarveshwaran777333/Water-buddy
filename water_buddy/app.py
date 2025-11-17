#FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"   # ← replace this
import streamlit as st
import requests
import hashlib

FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"  # replace this

# -----------------------------
# Password Hashing
# -----------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Firebase GET
def firebase_get(path):
    response = requests.get(FIREBASE_URL + path + ".json")
    return response.json()

# Firebase PUT
def firebase_put(path, data):
    response = requests.put(FIREBASE_URL + path + ".json", json=data)
    return response.json()


# =============================
# 🎨 THEME SETTINGS
# =============================
def apply_theme():
    theme = st.session_state.get("theme", "light")

    if theme == "dark":
        st.markdown(
            """
            <style>
            body { background-color: #0d1117; color: white; }
            .stButton>button { background-color: #222; color: white; }
            .stTextInput>div>div>input { background-color: #111; color: white; }
            </style>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <style>
            body { background-color: #ffffff; color: black; }
            .stButton>button { background-color: #e6e6e6; color: black; }
            </style>
            """,
            unsafe_allow_html=True
        )


# =============================
# 🏠 HOME PAGE
# =============================
def home_page():
    apply_theme()
    st.title("🏠 Home Page")
    st.write("This is the home page.")

    if st.button("Go to Settings"):
        st.session_state["current_page"] = "settings"
        st.rerun()


# =============================
# ⚙ SETTINGS PAGE
# =============================
def settings_page():
    apply_theme()
    st.title("⚙ Settings")

    st.subheader("🔵 Theme Selection")
    theme_choice = st.radio("Choose Theme", ["light", "dark"], index=0 if st.session_state["theme"] == "light" else 1)

    if theme_choice != st.session_state["theme"]:
        st.session_state["theme"] = theme_choice
        st.rerun()

    st.subheader("💧 Water Goal (mL)")
    current_goal = st.session_state.get("water_goal", 2000)

    new_goal = st.number_input("Set Water Goal (mL)", min_value=500, max_value=6000, value=current_goal)

    if st.button("Save Goal"):
        st.session_state["water_goal"] = new_goal
        st.success("Water goal updated!")

    st.write("---")

    if st.button("Go to Home Page"):
        st.session_state["current_page"] = "home"
        st.rerun()

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["user"] = None
        st.session_state["current_page"] = "login"
        st.rerun()


# =============================
# 🔐 LOGIN PAGE
# =============================
def login_page():
    apply_theme()
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users = firebase_get("users")

        if users and username in users:
            hashed = hash_password(password)
            if users[username]["password"] == hashed:

                st.session_state["logged_in"] = True
                st.session_state["user"] = username
                st.session_state["current_page"] = "settings"  # ➜ OPEN SETTINGS DIRECTLY
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Incorrect password!")
        else:
            st.error("User does not exist!")

    if st.button("Go to Signup"):
        st.session_state["current_page"] = "signup"
        st.rerun()


# =============================
# 📝 SIGNUP PAGE
# =============================
def signup_page():
    apply_theme()
    st.title("📝 Signup")

    username = st.text_input("Create Username")
    password = st.text_input("Create Password", type="password")

    if st.button("Signup"):
        users = firebase_get("users") or {}

        if username in users:
            st.error("Username already exists!")
        else:
            hashed = hash_password(password)
            firebase_put(f"users/{username}", {"password": hashed})
            st.success("Account created! Redirecting to Login...")
            st.session_state["current_page"] = "login"
            st.rerun()

    if st.button("Back to Login"):
        st.session_state["current_page"] = "login"
        st.rerun()


# =============================
# APP FLOW CONTROL
# =============================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "login"

if "theme" not in st.session_state:
    st.session_state["theme"] = "light"

# ---------- PAGE LOGIC ----------
if st.session_state["logged_in"]:
    if st.session_state["current_page"] == "settings":
        settings_page()
    elif st.session_state["current_page"] == "home":
        home_page()
else:
    if st.session_state["current_page"] == "signup":
        signup_page()
    else:
        login_page()
