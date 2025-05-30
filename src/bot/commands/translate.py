"""
This module implements the translation feature using ConversationHandler.

It allows users to:
- Choose a language to translate into
- Send a message for translation
- Receive the translated text
- Switch language or finish the session at any time

Main Components:
- choose_language: Sends an introductory message and shows language selection buttons.
- get_user_message: Handles language selection and asks for the message to translate.
- translate_user_message: Translates the provided user message using OpenAI and returns the result.
- change_language: Lets the user change the translation language.
- end_translate: Ends the translation session and returns to the main menu.
- translate_conv_handler: Handles the full conversation flow of the translation feature.
"""

from telegram import Update
from telegram.error import BadRequest
from openai import OpenAIError
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image
from bot.sanitize_html import sanitize_html
from bot.keyboards import get_choose_language_button, get_translate_menu_button
from bot.commands.start import start
from db.repository import GptThreadRepository
from db.enums import SessionMode, MessageRole
from services import OpenAIClient
from settings import config, get_logger


logger = get_logger(__name__)
TRANSLATE_MESSAGE = SessionMode.TRANSLATE.value


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends an introduction and shows language selection buttons.

    Loads intro text and image, then displays the language options.

    Args:
        update (telegram.Update): Incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing user/bot data.
    """

    intro = await load_message("translate")
    image_bytes = await load_image("translate")

    await send_image_bytes(update, context, image_bytes)
    await send_html_message(update, context, intro)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="What language do you want to translate into?",
        reply_markup=get_choose_language_button()
    )


async def get_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles language selection and prompts the user to enter a message for translation.

    Saves the selected language to context.user_data.

    Args:
        update (telegram.Update): Update triggered by pressing a language button.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object.

    Returns:
        TRANSLATE_MESSAGE (str): Conversation state for receiving user message to translate.
    """

    query = update.callback_query
    language = query.data

    await query.answer()

    context.user_data["language"] = language

    await send_html_message(update, context, f"Ok. You have selected {language.capitalize()}. Now enter a message to translate.")

    return TRANSLATE_MESSAGE


async def translate_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Translates the user's message using OpenAI assistant and returns the result.

    Creates a new OpenAI thread if one doesn't exist, stores messages in the database,
    and updates the Telegram user with the translated text.

    Args:
        update (telegram.Update): User text message.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object.

    Returns:
        TRANSLATE_MESSAGE (str): Keeps the conversation in the same state for further translations.

    Raises:
        OpenAIError: If OpenAI assistant fails.
        BadRequest: If the Telegram message is invalid or too long.
    """

    context.user_data["mode"] = None
    user_message = update.message.text
    language = context.user_data.get("language")

    if not language:
        await send_html_message(update, context, "⚠️ You have not selected a language yet. Please choose a language first.")
        return await choose_language(update, context)


    # Connecting the assistant and DB
    openai_client: OpenAIClient = context.bot_data["openai_client"]
    assistant_id = config.ai_assistant_translate_mileshkin_id
    thread_repository: GptThreadRepository = context.bot_data["thread_repository"]

    tg_user_id = update.effective_user.id
    mode = SessionMode.QUIZ.value

    thread_id = await thread_repository.get_thread_id(tg_user_id, mode)

    if thread_id is None:
        thread = await openai_client.create_thread()
        thread_id = thread.id
        await thread_repository.create_thread(tg_user_id, mode, thread_id)


    user_message_to_translate = f"Translate the text after 3 line breaks into {language}\n\n\n{user_message}"

    # Saving users message in DB
    await thread_repository.add_message(thread_id, role=MessageRole.USER.value, content=user_message_to_translate)

    # Get translate from assistant
    try:
        reply = await openai_client.ask(
            assistant_id=assistant_id,
            thread_id=thread_id,
            user_message=user_message_to_translate
        )
    except OpenAIError as e:
        logger.warning(f"Assistant failed to respond in /translate, translate_user_message(): {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return TRANSLATE_MESSAGE

    reply = sanitize_html(reply)

    # Saving assistants message in DB
    await thread_repository.add_message(thread_id, role=MessageRole.ASSISTANT.value, content=reply)

    # Sending the assistant's response to the user
    try:
        await send_html_message(update, context, reply)
    except BadRequest as e:
        logger.warning(f"Error sending HTML message in /translate, translate_user_message(): {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return TRANSLATE_MESSAGE

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send the following text for translation or:",
        reply_markup=get_translate_menu_button()
    )
    return TRANSLATE_MESSAGE


async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Restarts the conversation by allowing the user to choose another language.

    Args:
        update (telegram.Update): Callback query from inline button.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object.

    Returns:
        CHOOSE_LANGUAGE (function): Calls choose_language().
    """

    query = update.callback_query
    await query.answer()

    return await choose_language(update, context)


async def end_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ends the translation session and redirects to the main start menu.

    Args:
        update (telegram.Update): Callback query from inline button.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object.

    Returns:
        start (function): Calls the start handler.
    """
    query = update.callback_query
    await query.answer()

    return await start(update, context)


"""
Conversation handler for translation mode.

This handler manages the translation flow:
- Language selection
- Receiving user input for translation
- Sending translation request to OpenAI
- Returning translated text to user
- Changing language or ending the session

Entry points:
    - /translate command or language selection via button.

States:
    TRANSLATE_MESSAGE: Handles message input, translation, language switching, and menu interaction.

Fallbacks:
    - Change language or return to main menu via callbacks.
"""
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
        CallbackQueryHandler(end_translate, pattern="^end_translate$"),
        CommandHandler("start", start)
    ]
)