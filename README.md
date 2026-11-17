# Student Management App

A comprehensive Flask-based web application designed to help students manage their academic life, mental health, and personal growth.

## 🚀 Features

- **Personality Assessment**: Take a quiz to discover your personality type and get tailored career and growth suggestions.
- **Stress Management**: Monitor your stress levels with an assessment tool. Includes personalized AI-powered advice (OpenAI API integration).
- **Exam Planner**: Generate a dynamic 7-day study schedule based on your exam dates, priorities, and study habits.
- **Community Feed**: Share quotes and thoughts with other students, with like and comment functionality.
- **User Authentication**: Secure login and registration system for personalized tracking and history.
- **Dashboard**: Visualize your progress and statistics with interactive charts.

## 🛠️ Technology Stack

- **Backend**: Python (Flask)
- **Database**: MySQL
- **AI Integration**: OpenAI API (optional)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)

## 📋 Prerequisites

- Python 3.x
- MySQL Server
- OpenAI API Key (optional, for AI features)

## ⚙️ Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone <your-repo-link>
   cd student_managment
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Configuration**:
   - Create a MySQL database named `student_management`.
   - Update the database credentials in `app.py` if they differ from the defaults (root/root).
   - The application will automatically create the required tables on the first run. Account registrations save a username, full name, email, and hashed password in the `users` table.

4. **OpenAI Configuration (Optional)**:
   - Set the `OPENAI_API_KEY` environment variable.

5. **Run the application**:
   ```bash
   python app.py
   ```
   The app will be available at `http://localhost:5000`.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open-source and available under the MIT License.
