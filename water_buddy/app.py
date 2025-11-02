import streamlit as st
import random
import datetime
from streamlit_autorefresh import st_autorefresh

# 🌊 App Title
st.set_page_config(page_title="Water Buddy", page_icon="💧")
st.title("💧 Water Buddy – Your Smart Hydration Assistant")

# 🔄 Auto-refresh every 5 minutes (optional)
st_autorefresh(interval=5 * 60 * 1000, key="refresh")

# 📅 Display today's date
today = datetime.date.today()
st.write(f"📆 Today: {today.strftime('%A, %d %B %Y')}")

st.divider()

# ☁️ Step 1: Ask the user for the current climate
st.subheader("🌦️ What’s the weather like right now?")
climate = st.selectbox(
    "Choose your current climate:",
    ["☀️ Sunny", "🌤️ Cloudy", "🌧️ Rainy", "❄️ Cold", "🌫️ Humid", "🌪️ Windy"],
    index=0
)

# 🌡️ Step 2: Ask for temperature manually
temp = st.number_input(
    "🌡️ Enter approximate temperature (°C):",
    min_value=-10,
    max_value=50,
    value=30
)

st.divider()

# 💧 Step 3: Calculate water intake suggestion based on climate
if climate == "☀️ Sunny":
    suggestion = random.randint(10, 12)
    tip = "It's a hot day! Keep sipping water regularly. 🔆"
elif climate == "🌧️ Rainy":
    suggestion = random.randint(7, 9)
    tip = "Even when it rains, hydration matters! ☔"
elif climate == "🌫️ Humid":
    suggestion = random.randint(9, 11)
    tip = "Humidity makes you sweat more — drink up! 💦"
elif climate == "❄️ Cold":
    suggestion = random.randint(6, 8)
    tip = "Cold weather can trick you into drinking less water. Stay aware! ❄️"
elif climate == "🌤️ Cloudy":
    suggestion = random.randint(8, 10)
    tip = "Mild weather, but hydration keeps your focus sharp! ☁️"
else:
    suggestion = random.randint(8, 11)
    tip = "Windy weather? Hydration keeps you energized! 🌪️"

# 💬 Step 4: Display results
st.success(f"💧 Based on the {climate.lower()} weather and {temp}°C, "
           f"you should drink around **{suggestion} glasses of water today!**")

st.info(tip)

st.divider()

# 🧠 Step 5: Random motivational quote
quotes = [
    "Water is life. Keep it flowing! 💦",
    "Stay hydrated, stay focused. 🌊",
    "A hydrated body is a happy body! 😊",
    "Sip water, not excuses. 💧",
    "Hydration = Energy. Don’t skip it! ⚡"
]
st.caption(random.choice(quotes))

# 👣 Footer
st.markdown("---")
st.markdown("**Developed with 💙 using Streamlit**")
