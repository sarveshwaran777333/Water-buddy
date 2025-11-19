import streamlit as st
import random

# ------------------------------
# Session State (Data Storage)
# ------------------------------
if "intake" not in st.session_state:
    st.session_state.intake = 0
if "goal" not in st.session_state:
    st.session_state.goal = 0
if "age_group" not in st.session_state:
    st.session_state.age_group = None

# ------------------------------
# Standard Recommended Goals
# ------------------------------
standard_goals = {
    "6-12": 1600,
    "13-18": 2000,
    "19-50": 2500,
    "65+": 2000
}

# ------------------------------
# Sidebar Navigation
# ------------------------------
st.sidebar.title("WaterBuddy Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["1. Set Profile", "2. Track Intake", "3. Progress & Feedback"]
)


# ==========================================================
# PAGE 1: Set Profile (Age group & Daily Goal)
# ==========================================================
if page == "1. Set Profile":
    st.title("WaterBuddy - Set Your Profile")

    age = st.selectbox(
        "Select your age group:",
        ["6-12", "13-18", "19-50", "65+"]
    )

    st.session_state.age_group = age

    # Auto suggested goal
    suggested = standard_goals[age]
    st.write(f"Suggested daily goal for this age group: {suggested} ml")

    custom_goal = st.number_input(
        "Set your daily water goal (ml):",
        value=suggested,
        min_value=500,
        step=100
    )

    st.session_state.goal = custom_goal

    st.success(f"Daily goal saved: {custom_goal} ml")


# ==========================================================
# PAGE 2: Track Intake (Logging & Reset)
# ==========================================================
elif page == "2. Track Intake":
    st.title("WaterBuddy - Track Your Water Intake")

    if st.session_state.goal == 0:
        st.warning("Please set your profile and goal in Page 1 first.")
    else:
        st.write(f"Daily Goal: {st.session_state.goal} ml")
        st.write(f"Water consumed today: {st.session_state.intake} ml")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Add +250 ml"):
                st.session_state.intake += 250
                st.success("Logged 250 ml.")

        with col2:
            manual = st.number_input("Add custom amount (ml):", min_value=0, step=50)
            if st.button("Add"):
                st.session_state.intake += manual
                st.success(f"Logged {manual} ml.")

        if st.button("Reset Today"):
            st.session_state.intake = 0
            st.success("Daily log reset.")


# ==========================================================
# PAGE 3: Progress & Feedback
# ==========================================================
elif page == "3. Progress & Feedback":
    st.title("WaterBuddy - Progress Report")

    if st.session_state.goal == 0:
        st.warning("Please set your profile and goal in Page 1 first.")
    else:
        total = st.session_state.intake
        goal = st.session_state.goal

        remaining = max(goal - total, 0)
        percentage = min(int((total / goal) * 100), 100)

        st.write(f"Total consumed: {total} ml")
        st.write(f"Remaining: {remaining} ml")
        st.write(f"Completion: {percentage}%")

        # Progress Bar
        st.progress(percentage / 100)

        # Motivational Messages
        if percentage == 0:
            msg = "Let's start! Drink your first glass."
        elif percentage < 25:
            msg = "Good start! Keep going."
        elif percentage < 50:
            msg = "Nice! You’re getting there."
        elif percentage < 75:
            msg = "Great progress! Stay hydrated."
        elif percentage < 100:
            msg = "Almost there! One more push!"
        else:
            msg = "Excellent! You completed your hydration goal."

        st.info(msg)

        # Optional hydration tips
        tips = [
            "Your body is 70% water. Keep it fueled.",
            "Sip water throughout the day, not all at once.",
            "Carry a bottle to remind yourself to drink."
        ]

        st.write("Daily Tip:")
        st.success(random.choice(tips))
