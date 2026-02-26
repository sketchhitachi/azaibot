import time

user_last = {}

async def anti_spam(update):
    uid = update.message.from_user.id
    now = time.time()

    if uid in user_last and now - user_last[uid] < 1:
        await update.message.delete()
        return True

    user_last[uid] = now
    return False

async def anti_link(update):
    if "http" in update.message.text.lower():
        await update.message.delete()
        return True
    return False
