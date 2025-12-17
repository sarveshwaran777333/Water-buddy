## 1000411-K.Sarveshwaran-WaterBuddy — Daily Hydration Tracker

WaterBuddy is a Python-based web application built using Streamlit that helps users track and improve their daily water intake. The application addresses the common problem of people forgetting to drink enough water during busy daily routines. By providing goal-based tracking, visual feedback, and historical analysis, WaterBuddy encourages healthier hydration habits.

This application uses local JSON file storage instead of a cloud database, making it suitable for school-level academic submissions and offline execution.

---

## 1. Project Objective

The main objective of WaterBuddy is to design and develop an interactive software solution that promotes healthy hydration habits. The application allows users to record daily water intake, set personalized goals, and monitor progress over time through clear visual indicators.

---

## 2. Features

- User sign-up and login using username and password  
- Unique user identification with local data storage  
- Daily water intake logging with quick-add and custom input options  
- Automatic daily tracking based on the current date  
- Age-group-based recommended daily intake values  
- Customizable personal hydration goals  
- Visual progress tracking using a progress bar and animated water bottle  
- Milestone feedback at different completion levels  
- Seven-day water intake history with graphical representation  
- Unit conversion between cups and milliliters  
- Daily hydration tips to encourage consistency  
- Light, Aqua, and Dark interface themes  

---

## 3. Technologies Used

- Python 3  
- Streamlit  
- Matplotlib  
- JSON (local file-based storage)  
- Optional: streamlit-lottie for animations  

---

## 4. Application Structure

WaterBuddy/
- app.py – Main Streamlit application  
- water_data.json – Local storage file (auto-generated)  
- assets/progress_bar.json – Optional animation file  
- README.md – Project documentation  

---
## 5. Running the Application

1. Install the required dependencies
2. Run the application using streamlit cloud


## 6. Data Storage Design

All application data is stored locally in a JSON file named `water_data.json`. The file maintains a structured record of users, profile information, and daily water intake entries. Each user’s intake is stored by date, enabling historical analysis without the use of an external database.

This approach demonstrates effective use of file handling, dictionaries, and persistent data storage in Python.

## 7. Security Considerations

User passwords are stored in plain text for demonstration and educational purposes only. This implementation is not intended for production use and does not include encryption or advanced security measures.

---

## 8. Academic Context

This project was developed as an individual academic submission to demonstrate practical application of Python programming concepts in solving a real-world problem.

The project demonstrates:
- Use of Python functions and modular code design  
- Application of control structures and data validation  
- File input/output using JSON  
- State management and interactivity using Streamlit  
- Data visualization with Matplotlib  
- User-centered interface design  

---

## 9. Limitations

- No encrypted authentication system  
- Local storage only with no cloud synchronization  
- Requires manual execution via Streamlit  

---

## 10. Future Improvements

- Secure password hashing and authentication  
- Cloud-based database integration  
- Automated hydration reminders  
- Extended analytics (weekly and monthly reports)  
- Improved mobile responsiveness  

---

## 11. Conclusion

WaterBuddy successfully demonstrates how Python and Streamlit can be used to create an interactive and meaningful web application. By addressing a common health-related issue and combining data handling, visualization, and user interaction, the project meets academic requirements while providing a practical and engaging solution.

## 12. Author & Academic Context

Project Name: WaterBuddy – Daily Hydration Tracker  
Type: Individual Academic Project  
Purpose: To demonstrate practical application of Python programming concepts through a real-world problem (hydration tracking).

Key Learning Outcomes:
- Use of Python functions, dictionaries, and control structures
- File handling using local JSON storage
- Building interactive web applications with Streamlit
- Data visualization using Matplotlib
- Applying UI/UX design principles (themes, feedback, progress indicators)

This project was developed as part of a school assessment to showcase problem-solving skills, code organization, and user-focused application design.
