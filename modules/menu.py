from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    keyboard = [
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🎵 Music", callback_data="music")],
        [InlineKeyboardButton("💰 Economy", callback_data="economy")],
        [InlineKeyboardButton("⚙ Admin", callback_data="admin")]
    ]
    return InlineKeyboardMarkup(keyboard)
