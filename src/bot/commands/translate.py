from telegram import Update
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image, load_prompt
from .start import start
from bot.keyboards import get_choose_language_button, get_translate_menu_button
from services import OpenAIClient

from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

TRANSLATE_MESSAGE = "TRANSLATE"


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):

    intro = await load_message("translate")
    image_bytes = await load_image("translate")

    await send_image_bytes(update, context, image_bytes)
    await send_html_message(update, context, intro)

    context.user_data["system_prompt"] = await load_prompt("translate")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="What language do you want to translate into?",
        reply_markup=get_choose_language_button()
    )


async def get_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    language = query.data

    await query.answer()

    context.user_data["language"] = language

    await send_html_message(update, context, f"Ok. You have selected {language.capitalize()}. Now enter a message to translate.")

    return TRANSLATE_MESSAGE


async def translate_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text
    language = context.user_data.get("language")

    if not language:
        await send_html_message(update, context, "⚠️ You have not selected a language yet. Please choose a language first.")
        return await choose_language(update, context)

    user_message_to_translate = f"Translate the text after 3 line breaks into {language}\n\n\n{user_message}"
    print(user_message_to_translate)

    system_prompt = context.user_data.get("system_prompt", "")
    openai_client: OpenAIClient = context.bot_data["openai_client"]

    reply = await openai_client.ask(user_message=user_message_to_translate, system_prompt=system_prompt)

    await send_html_message(update, context, reply)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send the following text for translation or:",
        reply_markup=get_translate_menu_button()
    )

    return TRANSLATE_MESSAGE


async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    return await choose_language(update, context)


async def end_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    return await start(update, context)


translate_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("translate", choose_language),
        CallbackQueryHandler(get_user_message, pattern="^(english|french|german|italian|spanish|ukrainian)$")
    ],
    states={
        TRANSLATE_MESSAGE: [
            CallbackQueryHandler(get_user_message, pattern="^(english|french|german|italian|spanish|ukrainian)$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, translate_user_message),
            CallbackQueryHandler(change_language, pattern="^change_language$"),
            CallbackQueryHandler(end_translate, pattern="^end_translate$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(change_language, pattern="^change_language$"),
        CallbackQueryHandler(end_translate, pattern="^end_translate$")
    ]
)