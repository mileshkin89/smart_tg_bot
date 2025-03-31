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

def get_end_chat_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("End chat", callback_data="end_chat")]
    ])

def get_quiz_choose_topic_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Science", callback_data="science"),
        InlineKeyboardButton("Sport", callback_data="sport")],
        [InlineKeyboardButton("Art", callback_data="art"),
         InlineKeyboardButton("Cinema", callback_data="cinema")]
    ])

def get_quiz_menu_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Next question", callback_data="next_question_quiz"),
        InlineKeyboardButton("Change topic", callback_data="change_topic_quiz"),
        InlineKeyboardButton("Complete quiz", callback_data="end_quiz")]
    ])

def get_choose_language_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("English", callback_data="english"),
        InlineKeyboardButton("French", callback_data="french")],
        [InlineKeyboardButton("German", callback_data="german"),
         InlineKeyboardButton("Italian", callback_data="italian")],
        [InlineKeyboardButton("Spanish", callback_data="spanish"),
         InlineKeyboardButton("Ukrainian", callback_data="ukrainian")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
    ])

def get_translate_menu_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Change language", callback_data="change_language"),
        InlineKeyboardButton("Complete translate", callback_data="end_translate")]
    ])



















