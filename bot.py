import os
import sqlite3
import logging
import random
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
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


# ================= UI SYSTEM =================

def themed_text(user_id, text):
    cursor.execute("SELECT theme FROM users WHERE user_id=?", (user_id,))
    theme = cursor.fetchone()[0]

    if theme == "dark":
        return f"🌑 {text}"
    else:
        return f"🌕 {text}"


def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎵 Music", callback_data="music")],
        [InlineKeyboardButton("🖼 Profile", callback_data="profile")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🎮 Game", callback_data="game")],
        [InlineKeyboardButton("🌈 Theme", callback_data="theme")],
        [InlineKeyboardButton("💎 Premium", callback_data="premium")],
        [InlineKeyboardButton("🧠 AI Mode", callback_data="ai")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    text = themed_text(
        update.effective_user.id,
        "Welcome to Azai's Professional Bot\n\nUse menu below."
    )

    await update.message.reply_text(text, reply_markup=main_menu())


# ================= PROFILE CARD GENERATOR =================

async def generate_profile_card(user):
    width, height = 600, 300
    img = Image.new("RGB", (width, height), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, width, 80), fill=(0, 120, 255))
    draw.text((20, 20), "AZAI'S PROFILE CARD", fill="white")

    cursor.execute("SELECT premium, theme, messages FROM users WHERE user_id=?", (user.id,))
    data = cursor.fetchone()

    text = f"""
User: @{user.username}
Premium: {'Yes' if data[0] else 'No'}
Theme: {data[1]}
Messages: {data[2]}
"""

    draw.text((20, 120), text, fill="white")

    bio = BytesIO()
    bio.name = "profile.png"
    img.save(bio, "PNG")
    bio.seek(0)
    return bio


# ================= BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "profile":
        bio = await generate_profile_card(query.from_user)
        await query.message.reply_photo(photo=InputFile(bio))

    elif query.data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(messages) FROM users")
        total_messages = cursor.fetchone()[0] or 0

        text = themed_text(
            user_id,
            f"📊 Stats\nUsers: {total_users}\nMessages: {total_messages}"
        )

        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "leaderboard":
        cursor.execute("SELECT username, messages FROM users ORDER BY messages DESC LIMIT 5")
        top = cursor.fetchall()

        text = "🏆 Leaderboard\n\n"
        for i, user in enumerate(top, 1):
            text += f"{i}. @{user[0]} — {user[1]} msgs\n"

        await query.edit_message_text(text, reply_markup=main_menu())

    elif query.data == "theme":
        cursor.execute("SELECT theme FROM users WHERE user_id=?", (user_id,))
        current = cursor.fetchone()[0]
        new = "dark" if current == "light" else "light"
        cursor.execute("UPDATE users SET theme=? WHERE user_id=?", (new, user_id))
        conn.commit()

        await query.edit_message_text(
            f"Theme switched to {new}",
            reply_markup=main_menu()
        )

    elif query.data == "music":
        await query.edit_message_text("🎵 Send song name to search.")

    elif query.data == "game":
        number = random.randint(1, 10)
        context.user_data["game"] = number
        await query.edit_message_text("Guess number between 1-10")

    elif query.data == "premium":
        await query.edit_message_text(
            "💎 Premium system ready for payment integration.",
            reply_markup=main_menu()
        )

    elif query.data == "ai":
        context.user_data["ai_mode"] = True
        await query.edit_message_text(
            "🧠 AI Mode Enabled. Type message.",
            reply_markup=main_menu()
        )


# ================= MESSAGE HANDLER =================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_message(user_id)

    # Game logic
    if "game" in context.user_data:
        try:
            guess = int(update.message.text)
            number = context.user_data["game"]
            if guess == number:
                await update.message.reply_text("🎉 Correct!")
            else:
                await update.message.reply_text(f"❌ Wrong! Number was {number}")
            del context.user_data["game"]
            return
        except:
            pass

    # Music search (safe YouTube search link)
    if update.message.text.lower().startswith("music "):
        query = update.message.text[6:]
        link = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        await update.message.reply_text(f"🎵 Results:\n{link}")
        return

    # AI Mode
    if context.user_data.get("ai_mode"):
        await update.message.reply_text("🤖 AI: Smart mode coming soon (Add OpenAI key)")
        return

    await update.message.reply_text("Use menu for features.")


# ================= BROADCAST =================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    message = " ".join(context.args)
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for user in users:
        try:
            await context.bot.send_message(user[0], f"📢 {message}")
        except:
            pass

    await update.message.reply_text("Broadcast sent.")


# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Azai's Phase 2 Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
