import os
import sqlite3
import smtplib
import ssl
from email.message import EmailMessage

from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

DB_PATH = "leads.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            message TEXT NOT NULL,
            source TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_lead(name, email, phone, message, source):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO leads (name, email, phone, message, source)
        VALUES (?, ?, ?, ?, ?)
    """, (name, email, phone, message, source))
    conn.commit()
    conn.close()


def send_email(to_email, subject, body, reply_to=None):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    from_email = os.getenv("FROM_EMAIL", smtp_user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/lead", methods=["POST"])
def lead():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    message = request.form.get("message", "").strip()
    source = request.form.get("source", "website-form").strip()

    if not name or not email or not message:
        return "Missing required fields", 400

    save_lead(name, email, phone, message, source)

    owner_email = os.getenv("OWNER_EMAIL")

    owner_subject = f"New lead from {name}"
    owner_body = f"""
New lead received:

Name: {name}
Email: {email}
Phone: {phone}
Source: {source}

Message:
{message}
"""

    customer_subject = "Thanks for contacting us"
    customer_body = f"""
Hi {name},

Thanks for reaching out. We received your message and will get back to you soon.

Your message:
{message}

Best,
The team
"""

    try:
        send_email(owner_email, owner_subject, owner_body, reply_to=email)
        send_email(email, customer_subject, customer_body)
    except Exception as e:
        return f"Lead saved, but email failed: {e}", 500

    return redirect(url_for("thanks"))


@app.route("/thanks", methods=["GET"])
def thanks():
    return render_template("thanks.html")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)