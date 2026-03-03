import os
import sqlite3
import random
import requests
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")
YOUTUBE_KEY = os.getenv("YOUTUBE_KEY")
ADMIN_ID = 8406876136

# ================= DATABASE =================

conn = sqlite3.connect("azai.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    premium INTEGER DEFAULT 0,
    theme TEXT DEFAULT 'light',
    messages INTEGER DEFAULT 0,
    ai_used INTEGER DEFAULT 0,
    last_reset TEXT
)
""")
conn.commit()

# ================= HELPERS =================

def register_user(user):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, username, last_reset) VALUES (?, ?, ?)",
            (user.id, user.username, str(date.today()))
        )
        conn.commit()

def reset_ai_if_needed(user_id):
    cursor.execute("SELECT last_reset FROM users WHERE user_id=?", (user_id,))
    last = cursor.fetchone()[0]

    if last != str(date.today()):
        cursor.execute(
            "UPDATE users SET ai_used=0, last_reset=? WHERE user_id=?",
            (str(date.today()), user_id)
        )
        conn.commit()

def add_message(user_id):
    cursor.execute("UPDATE users SET messages=messages+1 WHERE user_id=?", (user_id,))
    conn.commit()

# ================= MENU =================

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎵 Music", callback_data="music")],
        [InlineKeyboardButton("🖼 Profile", callback_data="profile")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🌈 Theme", callback_data="theme")],
        [InlineKeyboardButton("💎 Premium", callback_data="premium")],
        [InlineKeyboardButton("🎮 Game", callback_data="game")],
        [InlineKeyboardButton("🧠 AI Mode", callback_data="ai")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)
    await update.message.reply_text(
        "✨ Welcome to Azai Pro Bot",
        reply_markup=main_menu()
    )

# ================= PROFILE IMAGE =================

def generate_profile(user_id, username, premium, theme, messages, ai_used):
    width, height = 700, 350
    bg = (25, 25, 25) if theme == "dark" else (240, 240, 240)
    text_color = (255, 255, 255) if theme == "dark" else (0, 0, 0)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    try:
        font_big = ImageFont.truetype("arial.ttf", 45)
        font_small = ImageFont.truetype("arial.ttf", 28)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    name = f"@{username}" if username else f"User {user_id}"

    draw.text((50, 50), name, font=font_big, fill=text_color)
    draw.text((50, 140), f"Messages: {messages}", font=font_small, fill=text_color)
    draw.text((50, 190), f"AI Used Today: {ai_used}", font=font_small, fill=text_color)
    draw.text((50, 240), f"Theme: {theme}", font=font_small, fill=text_color)

    if premium:
        draw.text((500, 50), "💎 PREMIUM", font=font_small, fill=(255, 215, 0))

    path = f"profile_{user_id}.png"
    img.save(path)
    return path

# ================= YOUTUBE =================

def search_youtube(query):
    if not YOUTUBE_KEY:
        return None

    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=1&q={query}&key={YOUTUBE_KEY}"
    r = requests.get(url).json()

    if "items" in r and len(r["items"]) > 0:
        v = r["items"][0]
        return (
            v["snippet"]["title"],
            v["snippet"]["channelTitle"],
            f"https://youtube.com/watch?v={v['id']['videoId']}"
        )
    return None

# ================= BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "profile":
        cursor.execute("SELECT premium, theme, messages, ai_used FROM users WHERE user_id=?", (user_id,))
        data = cursor.fetchone()

        img = generate_profile(
            user_id,
            query.from_user.username,
            data[0],
            data[1],
            data[2],
            data[3]
        )

        with open(img, "rb") as photo:
            await context.bot.send_photo(chat_id=user_id, photo=photo)

    elif query.data == "theme":
        cursor.execute("SELECT theme FROM users WHERE user_id=?", (user_id,))
        current = cursor.fetchone()[0]
        new = "dark" if current == "light" else "light"

        cursor.execute("UPDATE users SET theme=? WHERE user_id=?", (new, user_id))
        conn.commit()

        await query.edit_message_text(f"Theme switched to {new}", reply_markup=main_menu())

    elif query.data == "music":
        context.user_data["mode"] = "music"
        await query.edit_message_text("Send song name")

    elif query.data == "ai":
        context.user_data["mode"] = "ai"
        context.user_data["memory"] = []
        await query.edit_message_text("AI Mode activated")

    elif query.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(messages) FROM users")
        msgs = cursor.fetchone()[0] or 0
        await query.edit_message_text(f"Users: {users}\nMessages: {msgs}", reply_markup=main_menu())

    elif query.data == "leaderboard":
        cursor.execute("SELECT username, messages FROM users ORDER BY messages DESC LIMIT 5")
        top = cursor.fetchall()
        text = "🏆 Leaderboard\n\n"
        for i, u in enumerate(top, 1):
            text += f"{i}. @{u[0]} — {u[1]}\n"
        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "game":
        number = random.randint(1, 10)
        context.user_data["game"] = number
        await query.edit_message_text("Guess number 1-10")

# ================= MESSAGE HANDLER =================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(update.effective_user)
    add_message(user_id)
    reset_ai_if_needed(user_id)

    text = update.message.text

    # Game
    if "game" in context.user_data:
        try:
            if int(text) == context.user_data["game"]:
                await update.message.reply_text("Correct!")
            else:
                await update.message.reply_text("Wrong!")
            del context.user_data["game"]
            return
        except:
            pass

    # Music
    if context.user_data.get("mode") == "music":
        result = search_youtube(text)
        if result:
            await update.message.reply_text(f"{result[0]}\n{result[1]}\n{result[2]}")
        else:
            await update.message.reply_text("Not found.")
        return

    # AI
    if context.user_data.get("mode") == "ai":
        cursor.execute("SELECT premium, ai_used FROM users WHERE user_id=?", (user_id,))
        premium, used = cursor.fetchone()

        if not premium and used >= 10:
            await update.message.reply_text("Free AI limit reached (10/day)")
            return

        memory = context.user_data.get("memory", [])
        memory.append({"role": "user", "content": text})
        memory = memory[-6:]

        if OPENAI_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=memory
            )
            reply = response.choices[0].message.content
        else:
            reply = random.choice(["Interesting", "Tell me more", "Nice"])

        memory.append({"role": "assistant", "content": reply})
        context.user_data["memory"] = memory

        cursor.execute("UPDATE users SET ai_used=ai_used+1 WHERE user_id=?", (user_id,))
        conn.commit()

        await update.message.reply_text(reply)
        return

    await update.message.reply_text("Use menu.")

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
