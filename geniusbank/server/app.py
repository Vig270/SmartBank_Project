# app.py
import os
import sqlite3
import uuid
from flask import Flask, request, jsonify, render_template, redirect, session, url_for
from authlib.integrations.flask_client import OAuth
from database import Database  # your existing DB helper
from auth import Auth

auth = Auth()
app = Flask(__name__)
app.secret_key = "geniusbank_secret_for_local"  # hard-coded for dev

# ---------------- DB ----------------
DB = "../geniusbank.db"
db = Database(DB)

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- OAuth (GitHub) ----------------
oauth = OAuth(app)
github = oauth.register(
    name="github",
    client_id='Ov23libxTwf7KnCwJVJ4',
    client_secret='2bafe6bc929a3066630f895d564e66febed77be0',
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)

# ---------------- Web Pages ----------------
@app.route("/")
def home():
    user = session.get("user")
    return render_template("index.html", user=user)

@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return redirect("/")
    return render_template("dashboard.html", user=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/register_page")
def register_page():
    return render_template("register.html")

# ---------------- GITHUB ----------------
@app.route("/login/github")
def github_login():
    # Make sure this matches your GitHub OAuth App exactly:
    # e.g., http://127.0.0.1:5000/login/github/callback
    redirect_uri = url_for("github_callback", _external=True)
    
    # Generate the authorization redirect
    response = github.authorize_redirect(redirect_uri)
    
    # Print full URL for debugging
    print("GitHub OAuth URL:", response.headers['Location'])
    
    return response

@app.route("/login/github/callback")
def github_callback():
    token = github.authorize_access_token()
    gh_user = github.get("user").json()
    github_id = str(gh_user["login"])  # use login as user_id

    # Check if user exists in DB
    conn = get_db()
    existing = conn.execute("SELECT * FROM users WHERE user_id=?", (github_id,)).fetchone()
    if not existing:
        # Create user with default balance & plan
        conn.execute(
            "INSERT INTO users (user_id, name, balance, plan) VALUES (?, ?, ?, ?)",
            (github_id, gh_user["login"], 0, "FREE")
        )
        conn.commit()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (github_id,)).fetchone()
    conn.close()

    # Save in session
    session["user"] = {
        "id": user["user_id"],
        "name": user["name"],
        "balance": user["balance"],
        "plan": user["plan"]
    }
    return redirect("/dashboard")

# ---------------- Local Login ----------------
@app.route("/login_local", methods=["POST"])
def login_local():
    if request.is_json:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
    else:
        username = request.form.get("username")
        password = request.form.get("password")

    if not username or not password:
        return jsonify({"status": "error", "message": "Missing username or password"}), 400

    conn = get_db()
    # Query by user_id OR name
    user = conn.execute(
        "SELECT * FROM users WHERE user_id=? OR name=?",
        (username, username)
    ).fetchone()
    conn.close()

    if user and db.verify_password(user["password_hash"], user["salt"], password):
        session["user"] = {
            "id": user["user_id"],
            "name": user["name"],
            "balance": user["balance"],
            "plan": user["plan"]
        }
        if request.is_json:
            return jsonify({"status": "success", "user": session["user"]})
        return redirect("/dashboard")

    return jsonify({"status": "error", "message": "Invalid username or password"})

@app.route("/register", methods=["POST"])
def register():

    # Accept JSON (GUI) OR form (webpage)
    if request.is_json:
        data = request.get_json()
        user_id = data.get("user_id")
        name = data.get("name")
        password = data.get("password")
    else:
        user_id = request.form.get("user_id")
        name = request.form.get("name")
        password = request.form.get("password")

    if not user_id or not name or not password:
        return jsonify({"status":"error","message":"Missing fields"}), 400

    conn = get_db()

    existing = conn.execute(
        "SELECT * FROM users WHERE user_id=? OR name=?",
        (user_id, name)
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({"status":"error","message":"User already exists"}), 400

    password_hash, salt = auth.hash_password(password)

    conn.execute(
        """
        INSERT INTO users (user_id, name, password_hash, salt, balance, plan)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, name, password_hash, salt, 0, "FREE")
    )

    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify({"status": "success", "message": "User registered"})
    else:
        return redirect("/")
# --------------depo-----------------------------
@app.route("/deposit", methods=["POST"])
def deposit():
    data = request.get_json()
    user_id = data.get("user_id") or session["user"]["id"]
    amount = data.get("amount")

    if not user_id or amount is None:
        return jsonify({"status":"error","message":"Unauthorized"}), 401

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"status":"error","message":"User not found"}), 404

    # FREE plan limit check
    if user["plan"] == "FREE" and amount > 500:
        conn.close()
        return jsonify({
            "status":"error",
            "message":"FREE plan can only deposit up to $500 at a time. Upgrade to PRO for higher deposits."
        }), 403

    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    balance = conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()["balance"]
    conn.close()

    # Update session
    session["user"]["balance"] = balance

    return jsonify({"status":"success","balance":balance,"message":f"${amount} deposited"})

# ------------------- WITHDRAW ----------------
@app.route("/withdraw", methods=["POST"])
def withdraw():
    data = request.get_json()
    user_id = data.get("user_id") or session["user"]["id"]
    amount = data.get("amount")

    if not user_id or amount is None:
        return jsonify({"status":"error","message":"Unauthorized"}), 401

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"status":"error","message":"User not found"}), 404

    fee = 1 if user["plan"]=="FREE" else 0
    total = amount + fee
    if user["balance"] < total:
        conn.close()
        return jsonify({"status":"error","message":"Insufficient funds"}), 400

    conn.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (total,user_id))
    conn.commit()
    balance = conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()["balance"]
    conn.close()

    # Update session
    session["user"]["balance"] = balance

    return jsonify({
        "status":"success",
        "balance":balance,
        "amount":amount,
        "fee":fee,
        "message":f"${amount} withdrawn, fee ${fee}"
    })
# ---------------- Upgrade/Downgrade PRO ----------------
@app.route("/upgrade_pro", methods=["POST"])
def upgrade_pro():
    user_id = request.get_json().get("user_id") or session["user"]["id"]
    if not user_id:
        return jsonify({"status":"error","message":"Unauthorized"}), 401

    conn = get_db()
    conn.execute("UPDATE users SET plan='PRO' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    # Update session
    session["user"]["plan"] = "PRO"

    return jsonify({"status":"success","message":"Upgraded to PRO"})

@app.route("/downgrade_pro", methods=["POST"])
def downgrade_pro():
    user_id = request.get_json().get("user_id") or session["user"]["id"]
    if not user_id:
        return jsonify({"status":"error","message":"Unauthorized"}), 401

    conn = get_db()
    conn.execute("UPDATE users SET plan='FREE' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    # Update session
    session["user"]["plan"] = "FREE"

    return jsonify({"status":"success","message":"Downgraded to FREE"})

# ---------------- Balance ----------------
# ---------------- Balance ----------------
@app.route("/balance")
def balance():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"balance": 0, "plan": "FREE"})

    conn = get_db()
    user = conn.execute("SELECT balance, plan FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()

    if not user:
        return jsonify({"balance": 0, "plan": "FREE"})

    # Only return the info; do NOT touch session
    return jsonify({"balance": user["balance"], "plan": user["plan"]})

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)