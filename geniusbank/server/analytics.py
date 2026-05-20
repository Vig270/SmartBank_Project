# analytics.py
import matplotlib.pyplot as plt

class Analytics:
    def __init__(self, db):
        self.db = db

    def show_transaction_history(self, user_id):
        self.db.cursor.execute("""
        SELECT type, amount, timestamp
        FROM transactions
        WHERE user_id = ?
        ORDER BY timestamp DESC
        """, (user_id,))

        return self.db.cursor.fetchall()

    def show_spending_chart(self, user_id):
        self.db.cursor.execute("""
        SELECT amount, timestamp
        FROM transactions
        WHERE user_id = ? AND type = 'Withdrawal'
        """, (user_id,))

        data = self.db.cursor.fetchall()

        if not data:
            print("No spending data available.")
            return

        amounts = [row[0] for row in data]
        dates = [row[1] for row in data]

        plt.plot(dates, amounts)
        plt.title("Spending Trend")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
