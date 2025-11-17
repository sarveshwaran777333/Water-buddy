# app.py
"""
WaterBuddy - Streamlit app with Signup/Login + Settings + Home (Water tracker)
Per-user data stored in Firebase Realtime Database (REST).
"""

import streamlit as st
import requests
import hashlib
import datetime
import random
from typing import Optional, Dict, Any

# -----------------------
# CONFIG - CHANGE IF NEEDED
# -----------------------
FIREBASE_URL = "https://waterhydrator-9ecad-default-rtdb.asia-southeast1.firebasedatabase.app/"  # <- must end with '/'
REQUEST_TIMEOUT = 6  # seconds

# Age based default goals (ml)
AGE_GROUP_GOALS = {
    "6-12": 1600,
    "13-18": 2000,
    "19-50": 2500,
    "51-64": 2400,
    "65+": 2200
}

QUICK_LOG_ML = 250
CUP_ML = 240  # 1 cup ~ 240 ml

RANDOM_TIPS = [
    "Start your day with a glass of water.",
    "Carry a water bottle and sip often.",
    "Drink a small glass 20-30 minutes before a meal.",
    "Add fruit slices for flavor—natural motivation!",
    "Sipping regularly beats chugging later."
]


# -----------------------
# Firebase helper functions
# -----------------------
def firebase_get(path: str) -> Optional[Any]:
    """
    GET data from Firebase path (without leading slash). Returns parsed JSON or None.
    Example path: "users" or "data/username"
    """
    try:
        url = FIREBASE_URL + path + ".json"
        res = requests.get(url, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error("Unable to connect to Firebase. Check your FIREBASE_URL and network.")
        # For dev debugging, you can uncomment next line (don't show in production logs):
        # st.write("Firebase GET error:", e)
        return None


def firebase_put(path: str, payload: Any) -> Optional[Any]:
    """
    PUT data to Firebase (overwrites). Returns response JSON or None.
    """
    try:
        url = FIREBASE_URL + path + ".json"
        res = requests.put(url, json=payload, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error("Failed to write to Firebase.")
        # st.write("Firebase PUT error:", e)
        return None


def firebase_patch(path: str, payload: Any) -> Optional[Any]:
    """
    PATCH data to Firebase (merges).
    """
    try:
        url = FIREBASE_URL + path + ".json"
        res = requests.patch(url, json=payload, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error("Failed to update Firebase.")
        return None


# -----------------------
# Password hashing
# -----------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# -----------------------
# Session initialization
# -----------------------
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "login"  # default
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    if "water_data" not in st.session_state:
        # local default structure; will be replaced with Firebase data on login
        st.session_state.water_data = {
            "date": str(datetime.date.today()),
            "age_group": "19-50",
            "standard_goal": AGE_GROUP_GOALS["19-50"],
            "user_goal": AGE_GROUP_GOALS["19-50"],
            "intake_ml": 0,
            "logs": [],  # list of {time, amount, note}
            "milestones_announced": []
        }


# -----------------------
# Utilities: unit converters, bottle HTML, mascot message
# -----------------------
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
        return "🎉 Amazing — goal reached! Mascot does a happy dance."
    if percent >= 75:
        return "👏 So close! Mascot is cheering you on."
    if percent >= 50:
        return "👍 Halfway there — great job!"
    if percent >= 25:
        return "🙂 Nice start — keep sipping."
    if intake_ml == 0:
        re
