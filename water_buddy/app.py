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
        cups_in = st.number_input("Cups", min_value=0.0, value=0.0, step=0.5, key="conv_cups")
    with col2:
        ml_in = st.number_input("ml", min_value=0.0, value=0.0, step=50.0, key="conv_ml")
    if st.button("Convert cups → ml"):
        st.session_state.conv_ml = round(cups_to_ml(cups_in), 1)
        st.experimental_rerun()
    if st.button("Convert ml → cups"):
        st.session_state.conv_cups = round(ml_to_cups(ml_in), 2)
        st.experimental_rerun()
    # Show last conversions
    st.write(f"-> {st.session_state.get('conv_cups', '')} cups")
    st.write(f"-> {st.session_state.get('conv_ml', '')} ml")

# Main layout: Age, goal, logging
st.subheader("Set your profile & goal")

age_col, goal_col = st.columns([1,1])
with age_col:
    age_group = st.selectbox("Select age group", list(AGE_GOALS_ML.keys()), index=list(AGE_GOALS_ML.keys()).index(st.session_state.age_group) if st.session_state.age_group in AGE_GOALS_ML else 2)
    if age_group != st.session_state.age_group:
        st.session_state.age_group = age_group
        st.session_state.suggested_goal_ml = AGE_GOALS_ML[age_group]
        # if user hasn't intentionally changed goal, auto-update
        if st.session_state.user_goal_ml == 0 or st.session_state.user_goal_ml == st.session_state.suggested_goal_ml:
            st.session_state.user_goal_ml = st.session_state.suggested_goal_ml

with goal_col:
    suggested = AGE_GOALS_ML[age_group]
    st.write(f"Suggested goal for {age_group}: **{suggested} ml**")
    # allow manual override
    user_goal = st.number_input("Your daily goal (ml)", min_value=500, max_value=10000, value=int(st.session_state.get("user_goal_ml", suggested)), step=100, key="user_goal_input")
    st.session_state.user_goal_ml = int(user_goal)

st.markdown("---")
st.subheader("Log water")

col_log, col_history = st.columns([1, 1.2])
with col_log:
    # Quick log buttons
    if st.button(f"+{DEFAULT_QUICK_LOG_ML} ml"):
        add_intake(DEFAULT_QUICK_LOG_ML)
        st.experimental_rerun()  # to update visuals immediately
    # Custom input log
    custom = st.number_input("Add custom amount (ml)", min_value=0, value=0, step=50, key="custom_add")
    if st.button("Log custom amount"):
        if custom > 0:
            add_intake(custom)
            st.success(f"Added {custom} ml")
            st.experimental_rerun()
        else:
            st.warning("Enter an amount greater than 0 ml to log.")

    st.markdown("**Controls**")
    if st.button("Reset today's intake"):
        reset_day()
        st.info("Intake reset to 0 for the day.")
        st.experimental_rerun()

with col_history:
    st.write("**Today's activity**")
    st.write(f"Date: {st.session_state.date}")
    st.write(f"Total entries: {len(st.session_state.log_history)}")
    if st.session_state.log_history:
        # Show most recent logs (reverse order)
        for amt, ts in reversed(st.session_state.log_history[-8:]):
            st.write(f"- {amt} ml at {ts}")

# Calculations and Feedback
st.markdown("---")
st.subheader("Progress")

intake, remaining, percent = compute_progress()
st.metric(label="Total intake (ml)", value=f"{intake} ml", delta=f"-{remaining} ml to goal" if remaining>0 else "Goal reached!")
st.progress(int(percent / 100))

# Provide the SVG bottle (center)
svg = generate_bottle_svg(percent)
st.write("### Visual tracker")
st.components.v1.html(svg, height=360, scrolling=False)

# Motivational message based on progress (one-line)
if percent >= 100:
    st.success("You've hit your daily goal — outstanding! 🎉")
elif percent >= 75:
    st.info("Almost there — 75%+ done. Keep sipping!")
elif percent >= 50:
    st.info("Halfway! Great momentum — keep it up.")
elif percent >= 25:
    st.info("Nice start — 25% reached. Maintain steady intake.")
else:
    st.write("Let's get started — small sips add up!")

# Optional comparison panel
st.markdown("---")
comp_col1, comp_col2 = st.columns(2)
with comp_col1:
    st.write("Standard target")
    st.write(f"**{AGE_GOALS_ML[age_group]} ml**")
with comp_col2:
    st.write("Your target")
    st.write(f"**{st.session_state.user_goal_ml} ml**")

# End-of-day summary (simple)
st.markdown("---")
st.write("### End of session summary")
st.write(f"- Goal: {st.session_state.user_goal_ml} ml")
st.write(f"- Intake so far: {st.session_state.intake_ml} ml")
st.write(f"- Remaining: {remaining} ml")
st.write(f"- Progress: {percent:.1f}%")

# friendly close
st.caption("WaterBuddy keeps everything in your browser session (privacy-friendly). To keep a longer history, connect a backend or export logs to a file in the future.")

# debug / developer view toggle (optional)
if st.checkbox("Show debug info"):
    st.json({
        "session_state_keys": list(st.session_state.keys()),
        "intake_ml": st.session_state.intake_ml,
        "user_goal_ml": st.session_state.user_goal_ml,
        "date": st.session_state.date,
        "milestones": st.session_state.milestone_flags,
    })
