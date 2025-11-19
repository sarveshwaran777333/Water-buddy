import streamlit as st
import firebase_admin
from firebase_admin import credentials, db

# -------------------------------------------------
# FIREBASE CONFIG
# -------------------------------------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app"

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-admin-key.json")   # put your key file here
    firebase_admin.initialize_app(cred, {
        "databaseURL": FIREBASE_URL
    })

# -------------------------------------------------
# DATABASE HELPERS
# -------------------------------------------------
def create_user(username, password):
    ref = db.reference("users")
    if ref.child(username).get() is not None:
        return False, "User already exists"
    ref.child(username).set({"password": password})
    return True, "Account created"

def login_user(username, password):
    ref = db.reference(f"users/{username}")
    user = ref.get()
    if user and user.get("password") == password:
        return True
    return False

def save_water_log(username, amount):
    ref = db.reference(f"logs/{username}")
    ref.push({"amount": amount})

def get_logs(username):
    ref = db.reference(f"logs/{username}")
    logs = ref.get()
    return logs if logs else {}

# -------------------------------------------------
# THEMES
# -------------------------------------------------
def apply_theme(theme_name):
    if theme_name == "Light":
        st.markdown("""
            <style>
            .stApp { background-color: #ffffff; color:#000000 }
            .stSidebar, .stRadio, .stSelectbox label, .css-1q8dd3e {
              color:#000 !important;
            }
            </style>
        """, unsafe_allow_html=True)

    elif theme_name == "Aqua":
        st.markdown("""
            <style>
            .stApp { background-color: #e6fbff; color:#000000 }
            .stSidebar, .stRadio, .stSelectbox label, label, span, p, h1, h2, h3, h4, h5 {
              color:#003344 !important;
            }
            </style>
        """, unsafe_allow_html=True)

# -------------------------------------------------
# AUTH PAGES
# -------------------------------------------------
def signup_page():
    st.title("Create Account")
    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")

    if st.button("Sign Up"):
        if username.strip() == "" or password.strip() == "":
            st.error("Username and password required")
            return
        ok, msg = create_user(username, password)
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

def login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if login_user(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error("Invalid username/password")

    if st.button("Create Account"):
        st.session_state.page = "signup"
        st.rerun()

# -------------------------------------------------
# APP SCREENS
# -------------------------------------------------
def home_page():
    st.header(f"Welcome, {st.session_state.username}")
    st.write("This is your water tracking dashboard.")

def log_water_page():
    st.header("Log Water Intake")
    amount = st.number_input("Enter amount (ml)", 0, 2000, 250)
    if st.button("Save"):
        save_water_log(st.session_state.username, amount)
        st.success("Saved")

    logs = get_logs(st.session_state.username)
    if logs:
        st.subheader("Your past logs")
        for k, v in logs.items():
            st.write(f"{v['amount']} ml")

def settings_page():
    st.header("Settings")
    theme = st.selectbox("Choose Theme", ["Light", "Aqua"])
    st.session_state.theme = theme
    st.success("Theme applied. Reloading UI...")
    st.rerun()

# -------------------------------------------------
# SIDEBAR MENU
# -------------------------------------------------
def dashboard_layout():
    apply_theme(st.session_state.get("theme", "Light"))

    with st.sidebar:
        st.title("Navigate")
        choice = st.radio("", ["Home", "Log Water", "Settings", "Logout"])

    if choice == "Home":
        home_page()
    elif choice == "Log Water":
        log_water_page()
    elif choice == "Settings":
        settings_page()
    elif choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.page = "login"
        st.rerun()

# -------------------------------------------------
# MAIN APP FLOW
# -------------------------------------------------
def main():
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        if st.session_state.page == "login":
            login_page()
        elif st.session_state.page == "signup":
            signup_page()
    else:
        dashboard_layout()

# RUN
if __name__ == "__main__":
    main()
