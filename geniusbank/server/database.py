# database.py
import sqlite3
import hashlib
import os
import uuid
from datetime import datetime

class Database:
    def __init__(self, db_path="geniusbank.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    # ---------------- Tables ----------------
    def create_tables(self):
        # Users table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT UNIQUE,
            salt BLOB,
            password_hash BLOB,
            balance REAL DEFAULT 0,
            plan TEXT DEFAULT 'FREE',
            github_id TEXT
        )
        """)

        # Transactions table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            type TEXT,
            amount REAL,
            timestamp TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)
        self.conn.commit()

    # ---------------- Add User ----------------
    def add_user(self, name, password=None, github_id=None):
        """
        Adds a new user. If password is given, hashes it. GitHub users may have github_id instead.
        """
        user_id = str(uuid.uuid4())
        salt = None
        password_hash = None

        if password:
            salt = os.urandom(16)
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt,
                100_000
            )

        self.cursor.execute("""
            INSERT INTO users (user_id, name, salt, password_hash, balance, plan, github_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, salt, password_hash, 0, 'FREE', github_id))
        self.conn.commit()
        return user_id

    # ---------------- Password Verification ----------------
    def verify_password(self, stored_hash, stored_salt, provided_password):
        """
        Returns True if provided_password matches the stored_hash using the stored_salt.
        """
        if not stored_hash or not stored_salt:
            return False
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode(),
            stored_salt,
            100_000
        )
        return hashed == stored_hash

    # ---------------- Transactions ----------------
    def add_transaction(self, user_id, txn_type, amount):
        timestamp = datetime.now().isoformat()
        self.cursor.execute("""
            INSERT INTO transactions (user_id, type, amount, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user_id, txn_type, amount, timestamp))
        self.conn.commit()

    def get_transactions(self, user_id):
        self.cursor.execute("""
            SELECT type, amount, timestamp FROM transactions
            WHERE user_id=?
            ORDER BY timestamp ASC
        """, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]

    # ---------------- Balance and Plan ----------------
    def update_balance(self, user_id, amount):
        self.cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        self.conn.commit()

    def get_user(self, username=None, user_id=None):
        if username:
            return self.cursor.execute("SELECT * FROM users WHERE name=?", (username,)).fetchone()
        if user_id:
            return self.cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return None

    def change_plan(self, user_id, plan):
        self.cursor.execute("UPDATE users SET plan=? WHERE user_id=?", (plan, user_id))
        self.conn.commit()

    # ---------------- Utility ----------------
    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()