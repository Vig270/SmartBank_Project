import sqlite3

conn = sqlite3.connect("../geniusbank.db")
cursor = conn.cursor()

# Get ALL users (not just those with transactions)
cursor.execute("SELECT user_id, name FROM users")
users = cursor.fetchall()

print("\n===== ACCOUNT TRANSACTION SUMMARY =====\n")

for user_id, name in users:

    cursor.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN type='Deposit' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN type='Withdrawal' THEN amount ELSE 0 END), 0)
        FROM transactions
        WHERE user_id=?
    """, (user_id,))

    deposit, withdrawal = cursor.fetchone()
    balance = deposit - withdrawal

    print(f"User: {user_id} ({name})")
    print(f"  Total Deposits   : {deposit}")
    print(f"  Total Withdrawals: {withdrawal}")
    print(f"  Balance          : {balance}")
    print("-" * 40)

conn.close()