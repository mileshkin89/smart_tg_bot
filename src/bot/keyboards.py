from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
    ])

def get_random_menu_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="start"),
        InlineKeyboardButton("I want another fact", callback_data="random")]
    ])

def get_talk_menu_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Albert Einstein", callback_data="einstein"),
        InlineKeyboardButton("Napoleon Bonaparte", callback_data="napoleon")],
        [InlineKeyboardButton("Stephen King", callback_data="king"),
         InlineKeyboardButton("Freddie Mercury", callback_data="mercury")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
    ])

def end_chat_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("End chat", callback_data="end_chat")]
    ])