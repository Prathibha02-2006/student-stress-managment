from flask import Flask, render_template, request, session, redirect, url_for
import mysql.connector
import random
import os
import openai

# configure OpenAI API key from environment variable (set OPENAI_API_KEY)
# make sure the environment variable is defined before running the app
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    # optional: log a warning once when server starts
    print("WARNING: OpenAI API key not found. AI features will use default advice.")

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # needed for session management

# MySQL connection setup
# ensure student_management database has a users table

from werkzeug.security import generate_password_hash, check_password_hash

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="student_management"
)
cursor = db.cursor()

# create users table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
)
""")

# create personality table to record quiz results
cursor.execute("""
CREATE TABLE IF NOT EXISTS personality (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100),
    name VARCHAR(100),
    total_score INT,
    personality_type VARCHAR(50),
    weak_trait VARCHAR(100),
    suggestion TEXT,
    q1 INT DEFAULT 0,
    q2 INT DEFAULT 0,
    q3 INT DEFAULT 0,
    q4 INT DEFAULT 0,
    q5 INT DEFAULT 0,
    q6 INT DEFAULT 0,
    q7 INT DEFAULT 0,
    q8 INT DEFAULT 0,
    q9 INT DEFAULT 0,
    q10 INT DEFAULT 0
)
""")

# create stress table to record stress quiz responses
cursor.execute("""
CREATE TABLE IF NOT EXISTS stress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100),
    name VARCHAR(100),
    total_score INT,
    stress_level VARCHAR(50),
    weak_area VARCHAR(100),
    suggestion TEXT,
    q1 INT,
    q2 INT,
    q3 INT,
    q4 INT,
    q5 INT,
    q6 INT DEFAULT 0,
    interest VARCHAR(100),
    comment TEXT
)
""")

# create exam planner table to store user plans
cursor.execute("""
CREATE TABLE IF NOT EXISTS planner (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100),
    name VARCHAR(100),
    daily_hours FLOAT,
    chronotype VARCHAR(50),
    concentration VARCHAR(50),
    reminder VARCHAR(100),
    earliest_exam DATE,
    generated_schedule TEXT
)
""")

# migration: older tables might lack certain newer columns, attempt to add them safely
for tbl in ['stress','personality','planner']:
    try:
        cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN username VARCHAR(100)")
    except Exception:
        pass

# ensure stress table has all question columns and interest/comment for extended quiz
for col, definition in [
    ('q1', 'INT DEFAULT 0'),
    ('q2', 'INT DEFAULT 0'),
    ('q3', 'INT DEFAULT 0'),
    ('q4', 'INT DEFAULT 0'),
    ('q5', 'INT DEFAULT 0'),
    ('q6', 'INT DEFAULT 0'),
    ('interest', 'VARCHAR(100)'),
    ('comment', 'TEXT')
]:
    try:
        cursor.execute(f"ALTER TABLE stress ADD COLUMN {col} {definition}")
    except Exception:
        pass

# create posts table for user quotes/feed
try:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100),
        content TEXT,
        likes INT DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
except Exception:
    pass

# migration: add likes column if missing
try:
    cursor.execute("ALTER TABLE posts ADD COLUMN likes INT DEFAULT 0")
except Exception:
    pass

# migration: create comments table if not exists
try:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        post_id INT,
        username VARCHAR(100),
        text TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
except Exception:
    pass

# commit all DDL changes

db.commit()

# ensure default admin account exists (password "admin")
admin_pass = generate_password_hash('admin')
cursor.execute("SELECT id FROM users WHERE username='admin'")
if not cursor.fetchone():
    cursor.execute("INSERT INTO users (username,password_hash) VALUES (%s,%s)",
                   ('admin', admin_pass))
    db.commit()

@app.route('/')
def index():
    # if user already logged in send to dashboard otherwise go to login
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Personality check route
@app.route('/personality', methods=["GET", "POST"])
def personality():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == "POST":
        name = request.form['name']

        q1 = int(request.form['q1'])
        q2 = int(request.form['q2'])
        q3 = int(request.form['q3'])
        q4 = int(request.form['q4'])
        q5 = int(request.form['q5'])
        q6 = int(request.form['q6'])
        q7 = int(request.form['q7'])
        q8 = int(request.form['q8'])
        q9 = int(request.form['q9'])
        q10 = int(request.form['q10'])

        total_score = q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8 + q9 + q10

        if total_score <= 15:
            personality_type = "Introvert"
            avatar = "I"
            suggestion = "Try participating in group discussions and social activities."
            career = "Researcher, Developer, Analyst"
        elif total_score <= 30:
            personality_type = "Ambivert"
            avatar = "A"
            suggestion = "You have balanced traits. Improve leadership and confidence."
            career = "Manager, Journalist, Teacher"
        else:
            personality_type = "Extrovert"
            avatar = "E"
            suggestion = "You are confident and social. Work on emotional balance and listening skills."
            career = "Sales, PR, Public Speaker"

        traits = {
            "Social Interaction": q1,
            "Decision Making": q2,
            "Risk Taking": q3,
            "Emotional Control": q4,
            "Leadership Skills": q5,
            "Collaboration": q6,
            "Adaptability": q7,
            "Organization": q8,
            "Proactivity": q9,
            "Resilience": q10
        }
        weak_trait = min(traits, key=traits.get)

        # Prepare detailed analysis for results page
        details = []
        descriptions = {
            "Social Interaction": "Measures how comfortable you are in groups.",
            "Decision Making": "Reflects your confidence in making choices.",
            "Risk Taking": "Shows your openness to new learning risks.",
            "Emotional Control": "Indicates resilience under pressure.",
            "Leadership Skills": "Your tendency to lead group efforts.",
            "Collaboration": "Frequency of working with others.",
            "Adaptability": "Preference for routine vs change.",
            "Organization": "How well you keep your tasks structured.",
            "Proactivity": "Initiative vs waiting for instructions.",
            "Resilience": "Ease of adapting to new situations."
        }
        for trait, score in traits.items():
            details.append({
                "trait": trait,
                "score": score,
                "desc": descriptions.get(trait, ""),
                "explanation": "Great! Maintain this." if score >= 3 else "Focus on improving this."
            })

        # Check history
        cursor.execute("SELECT COUNT(*) FROM personality WHERE username=%s", (session.get('username'),))
        prev_count = cursor.fetchone()[0]
        history_msg = f"This is your {prev_count + 1} assessment."

        cursor.execute(
            "INSERT INTO personality (username, name, total_score, personality_type, weak_trait, suggestion, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (session.get('username'), name, total_score, personality_type, weak_trait, suggestion, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10)
        )
        db.commit()

        return render_template(
            "personality_results.html",
            total_score=total_score,
            personality_type=personality_type,
            weak_trait=weak_trait,
            suggestion=suggestion,
            avatar=avatar,
            career=career,
            history_msg=history_msg,
            details=details
        )
    return render_template("personality.html")

# Stress management route
@app.route('/stress', methods=["GET", "POST"])
def stress():
    if 'username' not in session:
        return redirect(url_for('login'))
    # show empty form on GET
    if request.method != "POST":
        return render_template("stress.html", total_score=None, comment=None)
    # otherwise handle submission
    name = request.form['name']

    q1 = int(request.form['q1'])
    q2 = int(request.form['q2'])
    q3 = int(request.form['q3'])
    q4 = int(request.form['q4'])
    q5 = int(request.form['q5'])
    # new question about workload
    q6 = int(request.form.get('q6', 0))
    # interest field (text/dropdown)
    interest = request.form.get('interest', 'General')
    # optional free-text comment about their stress/problems
    comment = request.form.get('comment', '').strip()

    total_score = q1 + q2 + q3 + q4 + q5 + q6

    # adjust thresholds for 6 questions (max 24)
    if total_score <= 10:
        stress_level = "Low"
        suggestion = "You are managing stress well. Maintain routine, exercise regularly and sleep properly."
    elif total_score <= 18:
        stress_level = "Moderate"
        suggestion = "Try meditation, short breaks during study, and light exercise."
    else:
        stress_level = "High"
        suggestion = "Practice deep breathing, yoga, talk to friends, reduce workload and improve sleep schedule."

    answers = {
        "Sleep Issues": q1,
        "Academic Pressure": q2,
        "Time Management": q3,
        "Social Pressure": q4,
        "Health/Fitness": q5,
        "Workload": q6
    }
    weak_area = max(answers, key=answers.get)

    # default suggestion based on score thresholds (will be replaced by AI if possible)
    suggestion = suggestion

    # ask AI for a truly personalised stress analysis if the API is configured
    if getattr(openai, 'api_key', None):  # type: ignore
        # build descriptive prompt including name, interest, and each answer
        prompt_lines = [
            f"Student name: {name}",
            f"Interest: {interest}",
            "The student answered the following ratings (1-5) for each factor:",
        ]
        for factor, val in answers.items():
            prompt_lines.append(f"- {factor}: {val}")
        prompt_lines.append(
            "\nPlease analyse the student's situation, identify the main problem areas, "
            "and give a friendly, professional, personalised paragraph of advice or coping strategies. "
            "Write as a personal adviser speaking directly to the student."
        )
        prompt = "\n".join(prompt_lines)
        try:
            # use ChatCompletion for better conversational control
            resp = openai.ChatCompletion.create( # type: ignore
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful, empathetic mental health advisor."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.7
            )
            ai_sugg = resp.choices[0].message.content.strip()  # type: ignore
            if ai_sugg:
                suggestion = ai_sugg
        except Exception:
            # if AI call fails, just ignore and keep default suggestion
            pass

    cursor.execute(
        "INSERT INTO stress (username, name, total_score, stress_level, weak_area, suggestion, q1, q2, q3, q4, q5, q6, interest, comment) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (session.get('username'), name, total_score, stress_level, weak_area, suggestion,
         q1, q2, q3, q4, q5, q6, interest, comment)
    )
    db.commit()

    # store score and interest for later use
    session['last_stress_score'] = total_score
    session['interest'] = interest

    ai_available = bool(getattr(openai, 'api_key', None))
    return render_template(
        "stress.html",
        total_score=total_score,
        stress_level=stress_level,
        weak_area=weak_area,
        suggestion=suggestion,
        comment=comment,
        ai_available=ai_available
    )
    return render_template("stress.html")

# Exam planner route
@app.route('/exam_planner', methods=["GET", "POST"])
def exam_planner():
    if 'username' not in session:
        return redirect(url_for('login'))

    timetable = None
    if request.method == "POST":
        name = request.form['name']
        daily_hours = float(request.form['daily_hours'])
        chronotype = request.form['chronotype']
        concentration = request.form['concentration']
        reminder = request.form['reminder']

        subjects = request.form.getlist('subject[]')
        priorities = request.form.getlist('priority[]')
        exam_dates_str = request.form.getlist('exam_date[]')

        # parse exam dates, take earliest exam date to cap schedule
        from datetime import datetime
        exam_dates = []
        for ds in exam_dates_str:
            try:
                exam_dates.append(datetime.strptime(ds, "%Y-%m-%d"))
            except Exception:
                pass
        if exam_dates:
            earliest_exam = min(exam_dates)
        else:
            earliest_exam = None

        # Assign weights based on priority
        subject_data = []
        for i in range(len(subjects)):
            weight = 3 if priorities[i] == "High" else 2 if priorities[i] == "Medium" else 1
            subject_data.append((subjects[i], weight))

        # Sort subjects by weight descending
        subject_data.sort(key=lambda x: x[1], reverse=True)

        # Determine start hour based on chronotype
        if chronotype == "Morning":
            start_hour = 6
            end_hour = 22  # Till 10 PM max
        else:
            start_hour = 16
            end_hour = 2 + 24  # Till 2 AM next day, so treat hours > 24 properly

        # Set block size by concentration level (in hours)
        if concentration == "High":
            block_size = 2
        elif concentration == "Medium":
            block_size = 1.5
        else:
            block_size = 1

        timetable = []
        current_hour = start_hour

        # We will create timetable for 7 days starting today with variability
        from datetime import datetime, timedelta
        start_date = datetime.today()

        days_count = 7
        for day_index in range(days_count):
            day_date = start_date + timedelta(days=day_index)
            # stop before exam day if known
            if earliest_exam and day_date >= earliest_exam:
                break
            date_str = day_date.strftime("%A (%d-%m-%Y)")

            # shuffle subject order each day
            random.shuffle(subject_data)

            # slightly vary start time relative to base start_hour
            jitter = random.uniform(-1.0, 1.0)
            day_start = start_hour + jitter
            # clamp within allowed range
            day_start = max(6, min(day_start, end_hour - 1))

            # adjust total available hours based on concentration and random factor
            hours_variation = daily_hours * random.uniform(-0.2, 0.2)
            day_hours = max(1.0, daily_hours + hours_variation)
            day_end = day_start + day_hours
            if day_end > end_hour:
                day_end = end_hour

            daily_schedule = []
            current_hour = day_start
            for subject, weight in subject_data:
                # adjust block size slightly per day
                size_jitter = block_size * random.uniform(0.85, 1.15)
                study_time = min(size_jitter * weight, day_hours)

                end_time = current_hour + study_time
                if end_time > day_end:
                    break

                daily_schedule.append({
                    "time": f"{format_time(current_hour)} - {format_time(end_time)}",
                    "subject": subject
                })
                current_hour = end_time

                # break length with minor randomness
                break_len = 0.5 + random.uniform(-0.1, 0.1)
                break_end = current_hour + break_len
                if break_end <= day_end:
                    daily_schedule.append({
                        "time": f"{format_time(current_hour)} - {format_time(break_end)}",
                        "subject": "Break"
                    })
                    current_hour = break_end

            timetable.append({
                "date": date_str,
                "schedule": daily_schedule
            })

        # save planner submission for history
        try:
            import json
            cursor.execute(
                "INSERT INTO planner (username, name, daily_hours, chronotype, concentration, reminder, earliest_exam, generated_schedule) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    session.get('username'),
                    name,
                    daily_hours,
                    chronotype,
                    concentration,
                    reminder,
                    earliest_exam.strftime('%Y-%m-%d') if earliest_exam else None,
                    json.dumps(timetable),
                )
            )
            db.commit()
        except Exception:
            pass

    return render_template("exam_planner.html", timetable=timetable)

# Helper to convert 24 hour float to 12-hour format with AM/PM
def format_time(hour_float):
    hour = int(hour_float) % 24
    minutes = int(round((hour_float - int(hour_float)) * 60))

    suffix = "AM" if hour < 12 else "PM"
    hour_12 = hour % 12
    if hour_12 == 0:
        hour_12 = 12

    return f"{hour_12}:{minutes:02d} {suffix}"



# challenge route
@app.route('/challenge', methods=['GET', 'POST'])
def challenge():
    if request.method == 'POST':
        days = int(request.form.get('days', 30))
        session['challenge_days'] = days
    else:
        days = session.get('challenge_days', 30)
    # original stress score from session
    # attempt to restore user-specific data from session or database
    orig_score = session.get('last_stress_score', 0)
    interest = session.get('interest')
    if 'username' in session:
        if orig_score == 0:
            cursor.execute("SELECT total_score FROM stress WHERE username=%s ORDER BY id DESC LIMIT 1", (session['username'],))
            row = cursor.fetchone()
            if row:
                orig_score = row[0]
                session['last_stress_score'] = orig_score
        if not interest:
            cursor.execute("SELECT interest FROM stress WHERE username=%s ORDER BY id DESC LIMIT 1", (session['username'],))
            row = cursor.fetchone()
            if row and row[0]:
                interest = row[0]
                session['interest'] = interest
    if not interest:
        interest = 'General'

    # basic fallback tasks grouped by interest
    interest_tasks = {
        'General': [
            'Meditate for 10 minutes',
            'Take a 20-minute walk',
            'Write down 3 things you are grateful for',
            'Do deep breathing exercises',
            'Read a chapter of a book',
            'Call a friend or family member',
            'Try a new healthy recipe',
            'Stretch for 15 minutes',
            'Listen to calming music',
            'Practice progressive muscle relaxation'
        ],
        'Exercise': [
            'Go for a short jog',
            'Do a 15-minute yoga session',
            'Try a bodyweight circuit',
            'Take a brisk walk outdoors',
            'Perform stretching exercises',
            'Ride a bicycle',
            'Do light strength training',
            'Follow a dance workout video',
            'Practice deep breathing after workout',
            'Swim or do water aerobics'
        ],
        'Art': [
            'Draw or doodle for 15 minutes',
            'Paint or colour something simple',
            'Visit a virtual museum',
            'Try a quick craft project',
            'Listen to relaxing instrumental music while sketching',
            'Create a gratitude collage',
            'Take photos of things you find beautiful',
            'Write a short poem',
            'Experiment with clay or playdough',
            'Make a simple origami figure'
        ],
        'Music': [
            'Listen to your favourite song and relax',
            'Try playing an instrument for 10 minutes',
            'Explore new genres of music',
            'Create a calming playlist',
            'Sing along to a cheerful tune',
            'Practice deep breathing while listening to ambient sounds',
            'Attend a virtual concert or music event',
            'Write down lyrics that inspire you',
            'Rhythmically tap or clap along to beats',
            'Learn a short melody online'
        ],
        'Reading': [
            'Read a chapter of an uplifting book',
            'Browse a favourite blog or article',
            'Explore a new author',
            'Write a short book review',
            'Read a poem aloud',
            'Read something in a genre you usually avoid',
            'Visit a library and explore',
            'Listen to an audiobook for 15 minutes',
            'Start a short story',
            'Read while sipping a warm drink'
        ],
        'Meditation': [
            'Try a guided meditation for beginners',
            'Practice mindful breathing for 10 minutes',
            'Listen to a meditation app session',
            'Take a quiet walk and focus on your senses',
            'Visualize a peaceful scene',
            'Do a body scan meditation',
            'Repeat a calming mantra',
            'Sit silently and observe your thoughts',
            'Practice progressive muscle relaxation',
            'Meditate before bed for relaxation'
        ],
        'Cooking': [
            'Prepare a healthy snack',
            'Try a new simple recipe',
            'Bake something you enjoy',
            'Cook a meal mindfully and slowly',
            'Plan a nutritious menu for the next day',
            'Explore a cuisine you’ve never tried',
            'Make a smoothie with fruits/veggies',
            'Organize your spice rack',
            'Share a meal with someone',
            'Watch a cooking tutorial and learn a new technique',
        ]
    }

    # choose base list by interest or fallback to general
    tasks = interest_tasks.get(interest, interest_tasks['General'])

    # optionally ask OpenAI to generate a custom list
    if openai:  # type: ignore
        try:
            prompt = (
                f"Generate a list of {days} simple daily stress-relief activities "
                f"for a student interested in {interest}. Provide one activity per line."
            )
            resp = openai.Completion.create( # type: ignore
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=days * 20,
                temperature=0.7
            )
            text = resp.choices[0].text.strip()
            ai_list = [line.strip('- ').strip() for line in text.splitlines() if line.strip()]
            if len(ai_list) >= days:
                tasks = ai_list
            else:
                # fill remainder from existing list
                tasks = (ai_list + tasks)[:days]
        except Exception:
            pass

    activities = []
    for i in range(1, days+1):
        task_item = tasks[(i-1) % len(tasks)]
        activities.append({'day': i, 'task': task_item})
    message = f'You have started a {days}-day challenge. Check back daily for reminders!'
    return render_template('challenge.html', days=days, activities=activities, message=message, orig_score=orig_score)


# Post-challenge questionnaire - same 5 questions to compare stress before/after
@app.route('/challenge_questions', methods=['GET', 'POST'])
def challenge_questions():
    if 'username' not in session:
        return redirect(url_for('login'))
    orig_score = session.get('last_stress_score', 0)
    if request.method == 'POST':
        q1 = int(request.form.get('q1', 1))
        q2 = int(request.form.get('q2', 1))
        q3 = int(request.form.get('q3', 1))
        q4 = int(request.form.get('q4', 1))
        q5 = int(request.form.get('q5', 1))
        new_score = q1 + q2 + q3 + q4 + q5
        diff = orig_score - new_score
        if diff > 0:
            diff_class = 'diff-improved'
            diff_text = f'-{diff} (Improved!)'
            message = 'Great job! Your stress level has decreased after the challenge.'
        elif diff < 0:
            diff_class = 'diff-worse'
            diff_text = f'+{abs(diff)} (Increased)'
            message = 'Your stress level increased. Consider continuing the challenge or trying additional stress-relief activities.'
        else:
            diff_class = 'diff-same'
            diff_text = '0 (No change)'
            message = 'Your stress level stayed the same. Keep practicing the challenge activities for better results.'
        return render_template('challenge_questions.html',
                               orig_score=orig_score,
                               new_score=new_score,
                               diff_class=diff_class,
                               diff_text=diff_text,
                               message=message)
    return render_template('challenge_questions.html')

# login/logout/dashboard routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # clear any leftover session data before logging in a new user
        session.clear()
        # check database for user
        cursor.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
        row = cursor.fetchone()
        if row and check_password_hash(row[0], password):
            session['username'] = username
            # preload last stress score and interest if available
            cursor.execute(
                "SELECT total_score, interest FROM stress WHERE username=%s ORDER BY id DESC LIMIT 1",
                (username,)
            )
            res = cursor.fetchone()
            if res:
                session['last_stress_score'] = res[0] or 0
                if res[1]:
                    session['interest'] = res[1]
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid credentials"
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    # clear all user-specific session data when logging out
    for key in ['username', 'last_stress_score', 'interest', 'challenge_days']:
        session.pop(key, None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # check exists
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            error = "Username already taken"
            return render_template('register.html', error=error)
        hash_val = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s,%s)",
                       (username, hash_val))
        db.commit()
        # log in user immediately
        session['username'] = username
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    # gather some basic stats from the database for current user
    user = session.get('username')
    cursor.execute("SELECT COUNT(*) FROM stress WHERE username=%s", (user,))
    total_stress = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(total_score) FROM stress WHERE username=%s", (user,))
    avg_stress = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM personality WHERE username=%s", (user,))
    total_personality = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(total_score) FROM personality WHERE username=%s", (user,))
    avg_personality = cursor.fetchone()[0] or 0

    # stress levels distribution
    cursor.execute("SELECT stress_level, COUNT(*) FROM stress WHERE username=%s GROUP BY stress_level", (user,))
    level_counts = dict(cursor.fetchall())

    # weak areas distribution for bar chart
    cursor.execute("SELECT weak_area, COUNT(*) FROM stress WHERE username=%s GROUP BY weak_area", (user,))
    weak_counts = dict(cursor.fetchall())

    # choose a consistent avatar background color based on username
    colors = ['#e74c3c','#8e44ad','#3498db','#16a085','#f39c12','#d35400','#2c3e50']
    username = session.get('username','')
    avatar_color = colors[hash(username) % len(colors)] if username else '#34495e'

    return render_template('dashboard.html',
                           total_stress=total_stress,
                           avg_stress=avg_stress,
                           total_personality=total_personality,
                           avg_personality=avg_personality,
                           level_counts=level_counts,
                           weak_counts=weak_counts,
                           avatar_color=avatar_color)

# simple social feed route
@app.route('/posts', methods=['GET', 'POST'])
def posts():
    if 'username' not in session:
        return redirect(url_for('login'))

    # handle new post submission
    if request.method == 'POST' and request.form.get('action') == 'post':
        content = request.form.get('content', '').strip()
        if content:
            cursor.execute(
                "INSERT INTO posts (username, content) VALUES (%s, %s)",
                (session['username'], content)
            )
            db.commit()
        return redirect(url_for('posts'))

    # handle like action
    if request.method == 'POST' and request.form.get('action') == 'like':
        pid = request.form.get('post_id')
        try:
            cursor.execute("UPDATE posts SET likes = likes + 1 WHERE id=%s", (pid,))
            db.commit()
        except Exception:
            pass
        return redirect(url_for('posts', page=request.args.get('page', 1)))

    # handle comment submission
    if request.method == 'POST' and request.form.get('action') == 'comment':
        pid = request.form.get('post_id')
        comment_text = request.form.get('comment_text','').strip()
        if pid and comment_text:
            cursor.execute(
                "INSERT INTO comments (post_id, username, text) VALUES (%s, %s, %s)",
                (pid, session.get('username'), comment_text)
            )
            db.commit()
        return redirect(url_for('posts', page=request.args.get('page', 1)))

    # pagination - 10 posts per page
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page
    cursor.execute("SELECT id, username, content, likes, created_at FROM posts ORDER BY created_at DESC LIMIT %s OFFSET %s", (per_page, offset))
    feed = cursor.fetchall()

    # fetch comments for each post displayed
    comments = {}
    for pid, *_ in feed:
        cursor.execute("SELECT id, username, text, created_at FROM comments WHERE post_id=%s ORDER BY created_at", (pid,))
        comments[pid] = cursor.fetchall()

    # determine if more posts exist for 'next' button
    cursor.execute("SELECT COUNT(*) FROM posts")
    total = cursor.fetchone()[0]
    more = offset + per_page < total

    return render_template('posts.html', feed=feed, comments=comments, page=page, more=more)

if __name__ == "__main__":
    app.run(debug=True)
