import os
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for
from datetime import datetime
from langdetect import detect
from dotenv import load_dotenv



app = Flask(__name__, static_folder='static')
load_dotenv()

# File paths
user_file_path = os.path.join("data", "users.json")
chat_logs_path = os.path.join("data", "chat_logs.json")
chat_history_path = os.path.join("data", "chat_history.json")
data_file_path = os.path.join("data", "data.json")
appointments_file_path = os.path.join("data", "appointments.json")

# Load data
with open(data_file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

# Define valid languages
valid_languages = ["en", "es", "fr", "ko", "ja", "de"]

faq_data = data["faq_data"]
common_phrases = data["common_phrases"]
keyword_responses = data["keyword_responses"]
exit_commands = data["exit_commands"]


# Initialize chat logs and history
chat_logs = []

def load_user_data():
    if os.path.exists(user_file_path):
        with open(user_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        return {}

def save_user_data(users):
    with open(user_file_path, 'w', encoding='utf-8') as file:
        json.dump(users, file, indent=4)

def load_appointments():
    appointments = []
    try:
        if os.path.exists(appointments_file_path):
            with open(appointments_file_path, 'r', encoding='utf-8') as file:
                appointments = json.load(file)
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {str(e)}")
    except Exception as e:
        print(f"Error loading appointments: {str(e)}")
    return appointments

def save_appointments(appointments):
    with open(appointments_file_path, 'w', encoding='utf-8') as file:
        json.dump(appointments, file, indent=4)

def save_appointment(appointment):
    appointments = load_appointments()
    appointments.append(appointment)
    with open(appointments_file_path, 'w', encoding='utf-8') as file:
        json.dump(appointments, file, indent=4)

def log_chat(message, sender):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    global chat_logs  # Ensure we access the global variable
    chat_logs.append({"timestamp": timestamp, "sender": sender, "message": message})

    # Save to chat_logs.json
    with open(chat_logs_path, "w", encoding="utf-8") as file:
        json.dump(chat_logs, file, indent=4)

    # Save to chat_history.json with sequential numbering
    history = []
    if os.path.exists(chat_history_path):
        with open(chat_history_path, "r", encoding="utf-8") as file:
            history = json.load(file)

    sequence_number = len(history) + 1
    history.append({
        "timestamp": timestamp,
        "sequence": sequence_number,
        "sender": sender,
        "message": message
    })

    with open(chat_history_path, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)

def check_common_phrases(user_input, language):
    if language in common_phrases:
        return common_phrases[language].get(user_input)
    return None

def check_exit_commands(user_input, language):
    if language in exit_commands and user_input in exit_commands[language]:
        return exit_commands[language][user_input]
    return None

def check_keyword_responses(user_input, language):
    if language in keyword_responses:
        for key, response in keyword_responses[language].items():
            if user_input in key.lower():
                return response
    return None

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_user_data()

        if username in users and users[username] == password:
            response = redirect(url_for("chat_page"))
            response.set_cookie("username", username)
            return response
        else:
            return render_template("index.html", error="User credentials are wrong")

    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        users = load_user_data()

        if username not in users:
            users[username] = password
            save_user_data(users)
            response = redirect(url_for("chat_page"))
            response.set_cookie("username", username)
            return response
        else:
            return render_template("register.html", error="Username already exists")

    return render_template("register.html")

@app.route("/chat")
def chat_page():
    username = request.cookies.get("username")
    if username:
        return render_template("chat.html", name=username)
    return redirect(url_for("login"))

@app.route("/get_response", methods=["POST"])
def get_response():
    data = request.get_json()
    user_input = data.get("user_input", "").lower().strip()  # Ensure lowercase and no leading/trailing spaces
    response = None

    log_chat(user_input, "user")

    # Language detection with fallback
    try:
        language = detect(user_input)
        if language not in valid_languages:
            raise ValueError(f"Detected language '{language}' is not supported.")
    except Exception as e:
        print(f"Language detection error: {e}")
        language = 'en'  # Default to English if language detection fails

    print(f"Detected language: {language}")
    if "appointment" in user_input:
        response = '<a href="/appointments">Click here to make an appointment</a>'
    if language in faq_data:
        for category, questions in faq_data[language].items():
            print(f"Category: {category}")
            print(f"Questions: {questions}")

            # Check for exact match of user_input in questions keys
            matched_question = next((q for q in questions.keys() if user_input == q.lower().strip()), None)
            if matched_question:
                response = questions[matched_question]
                break

    if response is None:
        response = check_common_phrases(user_input, language) or check_exit_commands(user_input, language) or check_keyword_responses(user_input, language) or "I'm sorry, I couldn't find an answer to your question."

    log_chat(response, "bot")

    return jsonify({"response": response})


@app.route("/book_appointment", methods=["POST"])
def book_appointment():
    try:
        appointment_data = request.form
        name = appointment_data.get("name")
        email = appointment_data.get("email")
        date = appointment_data.get("date")
        time = appointment_data.get("time")
        doctor = appointment_data.get("doctor")
        hospital = appointment_data.get("hospital")

        if not all([name, email, date, time]):
            return render_template("error.html", message="Incomplete data")

        appointments = load_appointments()
        appointments.append({
            "name": name,
            "email": email,
            "date": date,
            "time": time,
            "doctor": doctor,
            "hospital": hospital
        })
        save_appointments(appointments)

        return render_template("confirmation.html", name=name, date=date, time=time)

    except Exception as e:
        print(f"Error booking appointment: {str(e)}")
        return render_template("error.html", message="Failed to book appointment")

@app.route("/appointments")
def appointments():
    appointments = load_appointments()
    print("Appointments loaded:", appointments)  # Add this for debugging
    return render_template("appointments.html", appointments=appointments)

@app.route('/chat_history_view')
def chat_history_view():
    try:
        chat_history = load_chat_history()  # Ensure this function returns a suitable format
        return render_template("chat_history.html", chat_history=chat_history)
    except Exception as e:
        print(f"Error loading chat history: {str(e)}")
        # Handle the error appropriately, perhaps return an error page or message
        return "Error loading chat history"

def load_chat_history():
    history = []
    if os.path.exists(chat_history_path):
        with open(chat_history_path, 'r', encoding='utf-8') as file:
            history = json.load(file)
    return history

@app.route('/chat_logs_view')
def chat_logs_view():
    logs = load_chat_logs()
    return render_template('chat_logs.html', chat_logs=logs)


@app.route('/save_chat_logs', methods=['POST'])
def save_chat_logs():
    try:
        data = request.get_json()
        if data:
            with open(chat_logs_path, 'a', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
                file.write('\n')  # Ensure each log entry is on a new line
            return jsonify({"message": "Chat logs saved successfully."}), 200
        else:
            return jsonify({"error": "No data received."}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to save chat logs: {str(e)}"}), 500

def load_chat_logs():
    logs = []
    try:
        if os.path.exists(chat_logs_path):
            with open(chat_logs_path, 'r', encoding='utf-8') as file:
                logs = json.load(file)
    except Exception as e:
        print(f"Error loading chat logs: {str(e)}")
    print("Loaded logs:", logs)  # Check what's loaded
    return logs

@app.route("/add_appointment", methods=["POST"])
def add_appointment():
    try:
        appointment_data = request.form
        name = appointment_data.get("name")
        email = appointment_data.get("email")
        date = appointment_data.get("date")
        time = appointment_data.get("time")
        doctor = appointment_data.get("doctor")
        hospital = appointment_data.get("hospital")

        if not all([name, email, date, time, doctor, hospital]):
            return render_template("error.html", message="Incomplete data")

        appointment = {
            "name": name,
            "email": email,
            "date": date,
            "time": time,
            "doctor": doctor,
            "hospital": hospital
        }

        save_appointment(appointment)  # Function to save the appointment to appointments.json

        return redirect(url_for("appointments"))

    except Exception as e:
        print(f"Error adding appointment: {str(e)}")
        return render_template("error.html", message="Failed to add appointment")

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(port=3003, debug=True)
