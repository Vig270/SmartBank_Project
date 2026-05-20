# transactions.py
import datetime

class Transactions:
    PLAN_LIMITS = {
        "FREE": 500,
        "PRO": 5000
    }

    def __init__(self, db):
        self.db = db

    def deposit(self, user_id, amount):
        if amount <= 0:
            return "Invalid deposit amount."

        self.db.cursor.execute("SELECT plan, balance FROM users WHERE user_id = ?", (user_id,))
        user = self.db.cursor.fetchone()

        plan, balance = user
        limit = self.PLAN_LIMITS[plan]

        if amount > limit:
            return f"{plan} plan limit exceeded (${limit})"

        new_balance = balance + amount

        self.db.cursor.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (new_balance, user_id)
        )

        self.db.cursor.execute(
            "INSERT INTO transactions (user_id, type, amount, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, "Deposit", amount, str(datetime.datetime.now()))
        )

        self.db.commit()
        return "Deposit successful."

    def withdraw(self, user_id, amount):
        if amount <= 0:
            return "Invalid withdrawal amount."

        self.db.cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = self.db.cursor.fetchone()[0]

        total = amount + 1  # $1 fee

        if total > balance:
            return "Insufficient funds."

        new_balance = balance - total

        self.db.cursor.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (new_balance, user_id)
        )

        self.db.cursor.execute(
            "INSERT INTO transactions (user_id, type, amount, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, "Withdrawal", amount, str(datetime.datetime.now()))
        )

        self.db.commit()
        return "Withdrawal successful ($1 fee applied)."
