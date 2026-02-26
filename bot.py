from telegram.ext import *
from config import TOKEN
from database import db
from modules import menu, music, moderation, ai
import random, os

async def start(update, context):
    await update.message.reply_text(
        "🔥 ULTRA PRO BOT",
        reply_markup=menu.main_menu()
    )

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    if query.data == "profile":
        user = db.get_user(uid)
        await query.edit_message_text(
            f"👤 Profile\nXP: {user[1]}\nCoins: {user[2]}\nLevel: {user[3]}\nWarns: {user[4]}",
            reply_markup=menu.main_menu()
        )

    elif query.data == "economy":
        success = db.daily_reward(uid)
        if success:
            await query.edit_message_text("💰 Daily reward claimed +50 coins",
                                          reply_markup=menu.main_menu())
        else:
            await query.edit_message_text("⏳ Already claimed today",
                                          reply_markup=menu.main_menu())

    elif query.data == "music":
        context.user_data["music"] = True
        await query.edit_message_text("🎵 Send song name")

async def handle_message(update, context):
    if await moderation.anti_spam(update): return
    if await moderation.anti_link(update): return

    uid = update.message.from_user.id
    db.add_xp(uid, random.randint(5,10))
    db.add_coins(uid,1)

    if db.level_up(uid):
        await update.message.reply_text("🎉 Level Up!")

    if context.user_data.get("music"):
        file = await music.download_song(update.message.text)
        await update.message.reply_audio(audio=open(file,"rb"))
        os.remove(file)
        context.user_data["music"] = False
        return

    reply = ai.free_ai(update.message.text)
    await update.message.reply_text(reply)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
