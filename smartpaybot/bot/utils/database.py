# bot/utils/database.py
import sqlite3

conn = sqlite3.connect("smartpaybot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    user_id INTEGER PRIMARY KEY,
    stripe_session_id TEXT,
    paid INTEGER DEFAULT 0
)
""")
conn.commit()

def store_payment(user_id: int, session_id: str):
    cursor.execute("REPLACE INTO payments (user_id, stripe_session_id, paid) VALUES (?, ?, 0)", (user_id, session_id))
    conn.commit()

def mark_paid(user_id: int):
    cursor.execute("UPDATE payments SET paid = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def check_payment_status(user_id: int) -> bool:
    cursor.execute("SELECT paid FROM payments WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] == 1
