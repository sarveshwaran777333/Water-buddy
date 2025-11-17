# app.py
"""
WaterBuddy - Streamlit app implementing:
- Age-group selector with auto-suggested daily goal and manual adjustment
- Quick +250 ml logger and custom log input
- Reset for a new day
- Progress calculations: total, remaining, percentage
- Progress visuals: st.progress + a CSS 'bottle' fill animation
- Mascot responses at milestones
- Optional unit converter (cups <-> ml)
- Sidebar: random daily tip, logs history, theme toggle (aqua)
"""
import streamlit as st
import datetime
import random
from typing import List

# -----------------------
# Configuration / Defaults
# -----------------------
AGE_GROUP_GOALS = {
    "6-12": 1600,
    "13-18": 2000,
    "19-50": 2500,
    "51-64": 2400,
    "65+": 2200
}
QUICK_LOG_ML = 250
CUP_ML = 240  # define 1 cup as 240 ml approx

RANDOM_TIPS = [
    "Start your day with a glass of water — small habit, big win.",
    "Carry a bottle with measurements — small sips add up!",
    "Add a slice of lemon to water for a refreshing taste.",
    "Drink a glass of water 30 mins before meals to stay hydrated.",
    "If you feel tired, try a water break before a snack."
]

# -----------------------
# Helpers
# -----------------------
def init_session_state():
    """Initialize session state variables for the day."""
    today = datetime.date.today().isoformat()
    if "date" not in st.session_state or st.session_state.get("date") != today:
        st.session_state["date"] = today
        st.session_state["age_group"] = "19-50"
        st.session_state["standard_goal_ml"] = AGE_GROUP_GOALS[st.session_state["age_group"]]
        st.session_state["user_goal_ml"] = st.session_state["standard_goal_ml"]
        st.session_state["intake_ml"] = 0
        st.session_state["logs"] = []  # each item: (time_iso, amount_ml, note)
        st.session_state["milestones_announced"] = set()

def ml_to_cups(ml: int) -> float:
    return ml / CUP_ML

def cups_to_ml(cups: float) -> int:
    return int(round(cups * CUP_ML))

def add_log(amount_ml: int, note: str = ""):
    now_iso = datetime.datetime.now().isoformat(timespec="seconds")
    st.session_state["intake_ml"] += amount_ml
    st.session_state["logs"].append((now_iso, amount_ml, note))

def reset_day():
    st.session_state["date"] = datetime.date.today().isoformat()
    st.session_state["intake_ml"] = 0
    st.session_state["logs"] = []
    st.session_state["milestones_announced"] = set()
    # keep user goal & age selection

def percent_of_goal(intake_ml: int, goal_ml: int) -> float:
    if goal_ml <= 0:
        return 0.0
    return min(100.0, (intake_ml / goal_ml) * 100.0)

def mascot_message(percent: float, intake_ml: int, goal_ml: int) -> str:
    # change message based on progress
    if percent >= 100:
        return "🎉 Amazing — goal reached! Your mascot does a happy dance 🐢💧"
    if percent >= 75:
        return "👏 You're so close! Keep sipping — the mascot is cheering."
    if percent >= 50:
        return "👍 Great! You're halfway there. Mascot gives you a high-five."
    if percent >= 25:
        return "🙂 Nice start — keep it steady! Mascot is smiling."
    if intake_ml == 0:
        return "👋 Welcome! Let's start small — try a 250 ml sip."
    return "💧 Keep going — every sip counts."

def css_bottle(progress_pct: float, theme: str = "default") -> str:
    """
    Return HTML for a simple 'bottle' filled by progress_pct (0-100).
    We use inline CSS to keep it self-contained.
    """
    # Cap
    p = max(0, min(100, progress_pct))
    # colors depending on theme
    if theme == "aqua":
        bottle_border = "#66c2ff"
        fill_color = "#00bfff"
        bg = "#e6f9ff"
    else:
        bottle_border = "#1f77b4"
        fill_color = "#1e90ff"
        bg = "#f0f8ff"

    html = f"""
    <div style="width:140px; margin: 10px auto; background:{bg}; padding:10px; border-radius:12px;">
      <div style="border:4px solid {bottle_border}; border-radius:20px; height:320px; width:70px; margin:0 auto; position:relative; overflow:hidden; background:linear-gradient(#f8fbff,#eaf6ff);">
        <div style="position:absolute; bottom:0; left:0; width:100%; height:{p}%; background:{fill_color}; transition: height 0.7s ease-in-out; opacity:0.9;">
        </div>
      </div>
      <div style="text-align:center; font-size:13px; color:#333; margin-top:8px;">
        Bottle: {p:.0f}% filled
      </div>
    </div>
    """
    return html

# -----------------------
# App Initialization
# -----------------------
st.set_page_config(page_title="WaterBuddy 💧", layout="centered")
init_session_state()

# Theme toggle
with st.sidebar:
    st.title("WaterBuddy")
    theme_choice = st.radio("Theme", options=["default", "aqua"], index=0 if st.session_state.get("date") else 0)
    show_tips = st.checkbox("Show daily tip", value=True)
    if st.button("Reset today's data"):
        reset_day()
        st.success("Day reset — all logs cleared for today.")

    st.markdown("---")
    st.subheader("Unit converter")
    col1, col2 = st.columns(2)
    with col1:
        cups_in = st.number_input("Cups", min_value=0.0, format="%.2f", value=0.00, key="conv_cups")
    with col2:
        ml_in = st.number_input("ML", min_value=0, value=0, step=10, key="conv_ml")
    # convert on change button
    if st.button("Convert cups → ml"):
        ml_val = cups_to_ml(st.session_state["conv_cups"])
        st.session_state["conv_ml"] = ml_val
        st.experimental_rerun()
    if st.button("Convert ml → cups"):
        cups_val = ml_to_cups(st.session_state["conv_ml"])
        st.session_state["conv_cups"] = round(cups_val, 2)
        st.experimental_rerun()

# -----------------------
# Main App UI
# -----------------------
st.title("WaterBuddy 💧 — your friendly hydration tracker")
st.markdown("Friendly, lightweight, and privacy-first. Your data stays in this browser session.")

# Age group selector + standard goal
age_col, goal_col = st.columns([2,3])
with age_col:
    age_group = st.selectbox("Select your age group", options=list(AGE_GROUP_GOALS.keys()), index=list(AGE_GROUP_GOALS.keys()).index(st.session_state["age_group"]))
    st.session_state["age_group"] = age_group
    st.session_state["standard_goal_ml"] = AGE_GROUP_GOALS[age_group]

with goal_col:
    st.markdown("**Daily goal (auto-suggested)**")
    suggested = st.session_state["standard_goal_ml"]
    # allow manual adjustment
    user_goal = st.number_input("Set your daily goal (ml)", min_value=500, max_value=10000, step=50, value=st.session_state.get("user_goal_ml", suggested))
    st.session_state["user_goal_ml"] = user_goal
    st.caption(f"Suggested for {age_group}: {suggested} ml")

st.markdown("---")

# Logging interface
log_col, bottle_col = st.columns([2,1])
with log_col:
    st.header("Log your water")
    st.markdown("Quick buttons or enter a custom amount.")

    # Quick +250 ml button
    if st.button(f"+{QUICK_LOG_ML} ml"):
        add_log(QUICK_LOG_ML, note="quick sip")
        st.success(f"Added {QUICK_LOG_ML} ml")

    # Custom logging
    custom_amount = st.number_input("Custom amount (ml)", min_value=10, max_value=5000, step=10, value=250, key="custom_amount")
    custom_note = st.text_input("Note (optional)", placeholder="e.g., morning, after run")
    if st.button("Add custom amount"):
        add_log(int(custom_amount), note=custom_note)
        st.success(f"Added {int(custom_amount)} ml — {custom_note}")

    # Show logs
    st.markdown("**Today's logs**")
    if st.session_state["logs"]:
        for t, amt, note in reversed(st.session_state["logs"]):
            display_note = f" — {note}" if note else ""
            st.write(f"{t}: +{amt} ml{display_note}")
    else:
        st.info("No logs yet — try the +250 ml button!")

    # Reset button (extra prominent)
    if st.button("Reset / Start New Day", key="reset_button"):
        reset_day()
        st.success("Data reset. Ready for a fresh day!")

with bottle_col:
    # Calculations
    intake = st.session_state["intake_ml"]
    goal = st.session_state["user_goal_ml"]
    remaining = max(0, goal - intake)
    pct = percent_of_goal(intake, goal)

    st.markdown("### Today's progress")
    st.metric(label="So far (ml)", value=f"{intake} ml")
    st.metric(label="Remaining (ml)", value=f"{remaining} ml")
    st.metric(label="Percent of goal", value=f"{pct:.0f}%")

    # Show progress bar
    st.progress(int(pct))

    # Bottle (animated CSS)
    st.markdown(css_bottle(pct, theme=theme_choice), unsafe_allow_html=True)

    # Mascot / motivational message
    msg = mascot_message(pct, intake, goal)
    st.markdown(f"### {msg}")

    # Announce milestones once per day (25,50,75,100)
    milestones = [25, 50, 75, 100]
    for m in milestones:
        if pct >= m and m not in st.session_state["milestones_announced"]:
            st.session_state["milestones_announced"].add(m)
            st.balloons() if m == 100 else st.success(f"Milestone: {m}% reached! Keep it up.")

st.markdown("---")

# Optional: side-by-side standard vs user goal visualization
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Standard target")
    st.write(f"Age group: **{st.session_state['age_group']}**")
    st.write(f"Standard: **{st.session_state['standard_goal_ml']} ml**")
    st.write(f"Which is about **{ml_to_cups(st.session_state['standard_goal_ml']):.1f} cups**")
with col_b:
    st.subheader("Your target")
    st.write(f"Set target: **{st.session_state['user_goal_ml']} ml**")
    st.write(f"Which is about **{ml_to_cups(st.session_state['user_goal_ml']):.1f} cups**")

# Footer: random tip
if show_tips:
    tip = random.choice(RANDOM_TIPS)
    st.info(f"Tip of the moment: {tip}")

st.markdown("---")
st.write("Built with ❤️ — WaterBuddy keeps all data in your browser session (no server required).")

# End of app
