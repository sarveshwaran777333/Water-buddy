# app.py
"""
WaterBuddy - Streamlit implementation (Stage 4-6)
Features:
 - Age group selector with auto-suggested goal and manual override
 - Quick +250 ml log button and manual logging input
 - Reset today's intake
 - Store live state in st.session_state
 - Compute total intake, remaining, percentage
 - Progress bar and SVG animated water-bottle visualization
 - Milestone messages (25%, 50%, 75%, 100%)
 - Unit converter (ml <-> cups)
 - Random daily hydration tip in the sidebar
"""

import streamlit as st
import random
import math
from datetime import date

# --------------------------
# Configuration / constants
# --------------------------
AGE_GOALS_ML = {
    "6-12 (Child)": 1600,
    "13-18 (Teen)": 2000,
    "19-50 (Adult)": 2500,
    "51-64 (Mature Adult)": 2300,
    "65+ (Senior)": 2000,
}

DEFAULT_QUICK_LOG_ML = 250
CUPS_TO_ML = 236.588  # 1 US cup in ml (approx)

TIPS = [
    "Keep a filled bottle at your desk — visible cues help.",
    "Drink a glass (250 ml) after every bathroom break.",
    "Start your day with a glass of water.",
    "Add a slice of lemon or cucumber if you prefer flavored water.",
    "Set small goals: 1 glass every 45–60 minutes.",
    "Hydrate before meals — it helps digestion and satiety.",
    "Carry a reusable bottle — tracking becomes easier.",
    "Drink water after exercise — replace lost fluids.",
]

# --------------------------
# Utility functions
# --------------------------
def init_session():
    if "date" not in st.session_state or st.session_state.date != str(date.today()):
        # New day or fresh start: initialize
        st.session_state.date = str(date.today())
        st.session_state.intake_ml = 0
        st.session_state.age_group = "19-50 (Adult)"
        st.session_state.suggested_goal_ml = AGE_GOALS_ML[st.session_state.age_group]
        st.session_state.user_goal_ml = st.session_state.suggested_goal_ml
        st.session_state.milestone_flags = {"25": False, "50": False, "75": False, "100": False}
        st.session_state.log_history = []  # list of tuples (amount_ml, timestamp-string)
    # Ensure keys exist
    if "intake_ml" not in st.session_state:
        st.session_state.intake_ml = 0
    if "user_goal_ml" not in st.session_state:
        st.session_state.user_goal_ml = AGE_GOALS_ML.get(st.session_state.age_group, 2500)

def add_intake(amount_ml: int):
    amount_ml = max(0, int(amount_ml))
    st.session_state.intake_ml += amount_ml
    st.session_state.log_history.append((amount_ml, st.time.strftime("%H:%M:%S")))
    check_milestones()

def reset_day():
    st.session_state.intake_ml = 0
    st.session_state.milestone_flags = {"25": False, "50": False, "75": False, "100": False}
    st.session_state.log_history = []

def ml_to_cups(ml: float) -> float:
    return ml / CUPS_TO_ML

def cups_to_ml(cups: float) -> float:
    return cups * CUPS_TO_ML

def compute_progress():
    goal = max(1, int(st.session_state.user_goal_ml))
    intake = max(0, int(st.session_state.intake_ml))
    percent = min(100, (intake / goal) * 100)
    remaining = max(0, goal - intake)
    return intake, remaining, percent

def check_milestones():
    intake, remaining, percent = compute_progress()
    flags = st.session_state.milestone_flags
    messages = []
    # Check and set flags for 25,50,75,100
    for threshold in (25, 50, 75, 100):
        key = str(threshold)
        if percent >= threshold and not flags[key]:
            flags[key] = True
            messages.append(threshold)
    # display messages after updating flags
    for t in messages:
        if t == 100:
            st.success(f"🎉 Amazing! You reached 100% of your daily goal — Great job!")
        else:
            st.info(f"Nice! You've reached {t}% of your goal. Keep going!")

# SVG water-bottle generator: fill based on percentage (0-100)
def generate_bottle_svg(percent: float, width:int=120, height:int=320) -> str:
    percent = max(0, min(100, percent))
    inner_width = width - 30
    inner_height = height - 60
    fill_height = (percent / 100.0) * inner_height
    empty_height = inner_height - fill_height
    svg = f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <!-- Bottle outline -->
      <rect x="10" y="10" rx="18" ry="18" width="{width-20}" height="{height-20}" fill="none" stroke="#2B7AAB" stroke-width="4"/>
      <!-- Inner (water) area background -->
      <rect x="20" y="30" width="{inner_width}" height="{inner_height}" fill="#e6f5fb" rx="12" ry="12"/>
      <!-- Water fill -->
      <rect x="20" y="{30 + empty_height}" width="{inner_width}" height="{fill_height}" fill="#2B9FE3" rx="12" ry="12"/>
      <!-- Percentage text -->
      <text x="{width/2}" y="{height-10}" font-size="14" text-anchor="middle" fill="#023047">{percent:.0f}%</text>
    </svg>
    """
    return svg

# --------------------------
# Streamlit UI
# --------------------------
st.set_page_config(page_title="WaterBuddy", page_icon="💧", layout="centered")

st.title("WaterBuddy — your friendly hydration guide")
st.markdown("Track daily water intake, set an age-aware goal, and get motivating feedback.")

init_session()

# Sidebar: tips and quick info
with st.sidebar:
    st.header("Daily tip")
    st.write(random.choice(TIPS))
    st.markdown("---")
    st.write("Quick converter")
    col1, col2 = st.columns(2)
    with col1:
        cups_in = st.number_input("Cups", min_value=0.0, value=0.0,_
