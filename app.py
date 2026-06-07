from flask import Flask, render_template, request
import sqlite3
import os
import pdfplumber
import google.generativeai as genai
import json

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads folder automatically
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Gemini API
genai.configure(api_key="...")

model = genai.GenerativeModel("gemini-2.5-flash")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register():

    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            password TEXT
        )
    """)

    cursor.execute(
        "INSERT INTO users(email,password) VALUES(?,?)",
        (email, password)
    )

    conn.commit()
    conn.close()

    return "Registration Successful"


@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )

    user = cursor.fetchone()

    conn.close()

    if user:
        return render_template("dashboard.html")
    else:
        return "Invalid Email or Password"


@app.route("/upload", methods=["POST"])
def upload():

    file = request.files["resume"]

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)

    text = ""

    with pdfplumber.open(filepath) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    prompt = f"""
You are an AI Placement Mentor.

Return ONLY valid JSON.

{{
  "resume_score": 0,
  "placement_chance": 0,
  "top_skills": [],
  "strengths": [],
  "weaknesses": [],
  "missing_skills": [],
  "roadmap": {{
    "month1": [],
    "month2": [],
    "month3": []
  }}
}}

Analyze the resume and fill the JSON.

Resume:
{text}
"""

    response = model.generate_content(prompt)

    raw_text = response.text.strip()

    # Sometimes Gemini returns ```json ... ```
    raw_text = raw_text.replace("```json", "")
    raw_text = raw_text.replace("```", "")
    raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)

    except Exception:

        data = {
            "resume_score": 0,
            "placement_chance": 0,
            "top_skills": [],
            "strengths": ["AI output parsing failed"],
            "weaknesses": [],
            "missing_skills": [],
            "roadmap": {
                "month1": [],
                "month2": [],
                "month3": []
            }
        }

    return render_template(
        "analysis.html",
        data=data
    )
@app.route("/mock-interview")
def mock_interview():
    return render_template("mock_interview.html")

@app.route("/generate-interview", methods=["POST"])
def generate_interview():

    role = request.form["role"]

    prompt = f"""
Generate exactly 5 interview questions for a {role}.

Format:

Q1:
Q2:
Q3:
Q4:
Q5:
"""

    response = model.generate_content(prompt)

    questions = response.text

    return render_template(
        "interview_questions.html",
        questions=questions,
        role=role
    )
@app.route("/evaluate-interview", methods=["POST"])
def evaluate_interview():

    role = request.form["role"]

    answers = f"""

Q1 Answer:
{request.form['answer1']}

Q2 Answer:
{request.form['answer2']}

Q3 Answer:
{request.form['answer3']}

Q4 Answer:
{request.form['answer4']}

Q5 Answer:
{request.form['answer5']}

"""

    prompt = f"""
You are a senior technical interviewer.

Candidate Role:
{role}

Candidate Answers:

{answers}

Evaluate and give:

1. Technical Score /10
2. Communication Score /10
3. Confidence Score /10
4. Overall Score /10
5. Strengths
6. Weaknesses
7. Improvement Tips

Professional format.
"""

    response = model.generate_content(prompt)

    result = response.text

    return render_template(
        "interview_result.html",
        result=result
    )
@app.route("/company-prep")
def company_prep():
    return render_template("company_prep.html")
@app.route("/generate-company-prep", methods=["POST"])
def generate_company_prep():

    company = request.form["company"]

    prompt = f"""
You are a placement mentor.

For {company} provide:

1. Company Overview
2. Selection Process
3. Important Technical Topics
4. Aptitude Topics
5. Top HR Questions
6. Top Technical Questions
7. Resume Tips
8. Preparation Strategy

Professional format.
"""

    try:
        response = model.generate_content(prompt)
        result = response.text

    except Exception:
        result = "AI service unavailable. Please try again later."

    return render_template(
        "company_result.html",
        result=result,
        company=company
    )
if __name__ == "__main__":
    app.run(debug=True)