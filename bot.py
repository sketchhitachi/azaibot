import os
import sqlite3
import logging
import random
import requests
from datetime import datetime
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

logging.basicConfig(level=logging.INFO)

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
    joined_at TEXT
)
""")
conn.commit()


def register_user(user):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, username, joined_at) VALUES (?, ?, ?)",
            (user.id, user.username, str(datetime.now()))
        )
        conn.commit()


def add_message(user_id):
    cursor.execute("UPDATE users SET messages = messages + 1 WHERE user_id=?", (user_id,))
    conn.commit()


# ================= MENU =================

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎵 Music Search", callback_data="music")],
        [InlineKeyboardButton("🖼 Profile", callback_data="profile")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🌈 Theme", callback_data="theme")],
        [InlineKeyboardButton("💎 Premium", callback_data="premium")],
        [InlineKeyboardButton("🎮 Mini Game", callback_data="game")],
        [InlineKeyboardButton("🧠 AI Mode", callback_data="ai")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)
    await update.message.reply_text(
        "✨ Welcome to Azai Bot\n\nSelect option:",
        reply_markup=main_menu()
    )


# ================= YOUTUBE SEARCH =================

def search_youtube(query):
    if not YOUTUBE_KEY:
        return None

    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=1&q={query}&key={YOUTUBE_KEY}"
    response = requests.get(url)
    data = response.json()

    if "items" in data and len(data["items"]) > 0:
        video = data["items"][0]
        title = video["snippet"]["title"]
        channel = video["snippet"]["channelTitle"]
        video_id = video["id"]["videoId"]
        link = f"https://youtube.com/watch?v={video_id}"
        return title, channel, link
    return None


# ================= AI SYSTEM =================

def fallback_ai():
    responses = [
        "Interesting 🤔",
        "Tell me more 🔥",
        "That sounds cool 😎",
        "Explain that deeper.",
        "I'm learning daily!"
    ]
    return random.choice(responses)


def openai_reply(messages):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        return response.choices[0].message.content
    except:
        return fallback_ai()


# ================= PROFILE IMAGE =================

def generate_profile(username, premium, theme, messages, ai_used):
    width, height = 600, 300
    bg = (30, 30, 30) if theme == "dark" else (240, 240, 240)
    text_color = (255, 255, 255) if theme == "dark" else (0, 0, 0)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    try:
        font_big = ImageFont.truetype("arial.ttf", 40)
        font_small = ImageFont.truetype("arial.ttf", 25)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((40, 40), f"@{username}", font=font_big, fill=text_color)
    draw.text((40, 110), f"Messages: {messages}", font=font_small, fill=text_color)
    draw.text((40, 150), f"AI Used Today: {ai_used}", font=font_small, fill=text_color)
    draw.text((40, 190), f"Theme: {theme}", font=font_small, fill=text_color)

    if premium:
        draw.text((400, 40), "💎 PREMIUM", font=font_small, fill=(255, 215, 0))

    path = f"profile_{username}.png"
    img.save(path)
    return path


# ================= BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "music":
        context.user_data["mode"] = "music"
        await query.edit_message_text("🎵 Send song name")

    elif query.data == "ai":
        context.user_data["mode"] = "ai"
        context.user_data["memory"] = []
        await query.edit_message_text("🧠 AI Mode activated")

    elif query.data == "profile":
        cursor.execute("SELECT premium, theme, messages, ai_used FROM users WHERE user_id=?", (user_id,))
        data = cursor.fetchone()

        image = generate_profile(
            query.from_user.username,
            data[0],
            data[1],
            data[2],
            data[3]
        )

        await context.bot.send_photo(chat_id=user_id, photo=open(image, "rb"))

    elif query.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(messages) FROM users")
        msgs = cursor.fetchone()[0] or 0
        await query.edit_message_text(
            f"📊 Users: {users}\n💬 Messages: {msgs}",
            reply_markup=main_menu()
        )

    elif query.data == "leaderboard":
        cursor.execute("SELECT username, messages FROM users ORDER BY messages DESC LIMIT 5")
        top = cursor.fetchall()
        text = "🏆 Leaderboard\n\n"
        for i, user in enumerate(top, 1):
            text += f"{i}. @{user[0]} — {user[1]}\n"
        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "theme":
        cursor.execute("SELECT theme FROM users WHERE user_id=?", (user_id,))
        current = cursor.fetchone()[0]
        new = "dark" if current == "light" else "light"
        cursor.execute("UPDATE users SET theme=? WHERE user_id=?", (new, user_id))
        conn.commit()
        await query.edit_message_text(f"Theme switched to {new}", reply_markup=main_menu())

    elif query.data == "premium":
        await query.edit_message_text("Premium gives unlimited AI access", reply_markup=main_menu())

    elif query.data == "game":
        number = random.randint(1, 10)
        context.user_data["game"] = number
        await query.edit_message_text("🎮 Guess number 1-10")


# ================= MESSAGE HANDLER =================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_message(user_id)
    text = update.message.text

    # Game
    if "game" in context.user_data:
        try:
            guess = int(text)
            if guess == context.user_data["game"]:
                await update.message.reply_text("🎉 Correct!")
            else:
                await update.message.reply_text("❌ Wrong!")
            del context.user_data["game"]
            return
        except:
            pass

    # Music
    if context.user_data.get("mode") == "music":
        result = search_youtube(text)
        if result:
            title, channel, link = result
            await update.message.reply_text(f"🎵 {title}\n👤 {channel}\n🔗 {link}")
        else:
            await update.message.reply_text("Not found or API missing.")
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
            reply = openai_reply(memory)
        else:
            reply = fallback_ai()

        memory.append({"role": "assistant", "content": reply})
        context.user_data["memory"] = memory

        cursor.execute("UPDATE users SET ai_used = ai_used + 1 WHERE user_id=?", (user_id,))
        conn.commit()

        await update.message.reply_text(reply)
        return

    await update.message.reply_text("Use menu.")


# ================= ADMIN PREMIUM =================

async def givepremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) == 1:
        target = int(context.args[0])
        cursor.execute("UPDATE users SET premium=1 WHERE user_id=?", (target,))
        conn.commit()
        await update.message.reply_text("Premium granted")


# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("givepremium", givepremium))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
