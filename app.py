from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import google.generativeai as genai
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '[YOUR_SECRET_KEY]'

genai.configure(api_key="[API_KEY]")

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    generation_config=generation_config,
    safety_settings=safety_settings
)

convo = model.start_chat(history=[])

def init_db():
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            email TEXT NOT NULL UNIQUE,
                            password TEXT NOT NULL)''')
        conn.commit()

def init_calories_db():
    with sqlite3.connect("calories.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS calories (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            calorie_change INTEGER NOT NULL,
                            FOREIGN KEY(user_id) REFERENCES users(id))''')
        conn.commit()

@app.route('/page')
def page():
    return render_template('register.html')

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        if user:
            flash('Email already registered!', 'error')
            return redirect(url_for('index'))

        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, hashed_password))
        conn.commit()

    flash('Registration successful!', 'success')
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))

        flash('Invalid email or password!', 'error')
        return redirect(url_for('index'))

@app.route('/dashboard', methods=["GET", "POST"])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    api_response = None

    if request.method == "POST":
        food = request.form["food"]
        option = request.form["type"]
        calories = request.form["calories_burned"]

        convo.send_message(f'This user ate {food}, it was {option}, how many calories did he gain approxamated? He also burned {calories} calories. Based on this, what is his calorie overall loss or gain. Your response should be in this format:"Based on the given information, I would approxamate that you gained [X] calories from the food that you ate. However due to your calorie loss, your overall weight gain/loss(specify if they gained or lost weight) is [Y] calories"')
        response = convo.last.text
        api_response = response

    return render_template("dashboard.html", api_response=api_response)

@app.route('/add_to_stats', methods=["POST"])
def add_to_stats():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    calorie_change = request.form['calorie_change']
    user_id = session['user_id']

    with sqlite3.connect("calories.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO calories (user_id, calorie_change) 
                          VALUES (?, ?)''', (user_id, calorie_change))
        conn.commit()

    flash('Calorie change added to stats!', 'success')
    return redirect(url_for('dashboard'))

@app.route("/stats", methods=["GET", "POST"])
def stats():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']
    calorie_changes = []

    with sqlite3.connect("calories.db") as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT calorie_change FROM calories WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()

        for row in rows:
            calorie_changes.append(row[0])

    print("User's Calorie Changes:", calorie_changes)

    return render_template("stats.html", calorie_changes=calorie_changes)


if __name__ == "__main__":
    init_db()
    init_calories_db()
    app.run(debug=True)
