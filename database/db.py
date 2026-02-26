import sqlite3
import time

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    xp INTEGER DEFAULT 0,
    coins INTEGER DEFAULT 100,
    level INTEGER DEFAULT 1,
    warns INTEGER DEFAULT 0,
    last_daily INTEGER DEFAULT 0
)
""")

conn.commit()

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def get_user(user_id):
    add_user(user_id)
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def add_xp(user_id, amount):
    add_user(user_id)
    cursor.execute("UPDATE users SET xp=xp+? WHERE user_id=?", (amount,user_id))
    conn.commit()

def add_coins(user_id, amount):
    add_user(user_id)
    cursor.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount,user_id))
    conn.commit()

def level_up(user_id):
    user = get_user(user_id)
    xp = user[1]
    level = user[3]

    if xp >= level * 100:
        cursor.execute("UPDATE users SET level=level+1 WHERE user_id=?", (user_id,))
        conn.commit()
        return True
    return False

def add_warn(user_id):
    cursor.execute("UPDATE users SET warns=warns+1 WHERE user_id=?", (user_id,))
    conn.commit()

def daily_reward(user_id):
    user = get_user(user_id)
    now = int(time.time())

    if now - user[5] >= 86400:
        cursor.execute("UPDATE users SET coins=coins+50, last_daily=? WHERE user_id=?", (now,user_id))
        conn.commit()
        return True
    return False
