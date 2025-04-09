"""
This module implements the logic for the "Talk with a historical figure" feature.

It uses Telegram's ConversationHandler to let the user choose one of four personalities
(Albert Einstein, Napoleon Bonaparte, Stephen King, Freddie Mercury) and chat with a
simulated assistant that responds in the style of that character.

Features:
- User selects a personality via inline buttons.
- Persistent thread management for OpenAI Assistant.
- Message history saved in the local SQLite database.

Main Components:
- choose_personality: Sends an introductory message and shows personality selection buttons.
- start_dialogue: Triggered when the user selects a personality. Saves the choice and notifies the user.
- chat_with_personality: Handles user messages, interacts with the assistant, and returns its reply.
- end_chat: Ends the chat session and returns to the main menu.
- talk_conv_handler: ConversationHandler that manages the dialogue states, transitions, and fallbacks.
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
from bot.keyboards import get_talk_menu_button, get_end_chat_button
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image
from bot.sanitize_html import sanitize_html
from db.repository import GptThreadRepository
from db.enums import SessionMode, MessageRole
from services import OpenAIClient
from settings import config, get_logger
from .start import start


logger = get_logger(__name__)
TALK_MESSAGE, CHOOSE_PERSONALITY = SessionMode.TALK.value, SessionMode.CHOOSE_PERSONALITY.value


async def choose_personality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends the intro message and lets the user choose a personality to chat with.

    Displays an image and a text explanation, then shows personality selection buttons.

    Args:
        update (telegram.Update): The incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing bot and user data.

    Returns:
        CHOOSE_PERSONALITY (str): The state where the bot expects a personality selection.
    """
    intro = await load_message("talk")
    image_bytes = await load_image("talk")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=intro)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Who would you like to ask a question?",
        reply_markup=get_talk_menu_button()
    )
    return CHOOSE_PERSONALITY



async def choose_personality_warning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Warns the user if they attempt to chat without selecting a personality.

    Args:
        update (telegram.Update): The incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing bot and user data.

    Returns:
        CHOOSE_PERSONALITY (str): The state remains unchanged until personality is selected.
    """
    await send_html_message(update, context, "Please choose a personality from the buttons before starting the conversation.")
    return CHOOSE_PERSONALITY



async def start_dialogue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the callback after the user selects a personality.

    Saves the selected personality to user_data and notifies the user.

    Args:
        update (telegram.Update): The incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing bot and user data.

    Returns:
        TALK_MESSAGE (str): The state where the assistant expects the user message.
    """
    query = update.callback_query
    personality = query.data

    context.user_data["personality"] = personality

    await query.answer()
    await send_html_message(update, context, f"You chose {personality.capitalize()}. Start a conversation!")

    return TALK_MESSAGE



async def chat_with_personality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles user messages and sends them to the selected assistant.

    Fetches or creates an OpenAI thread, stores the user's message, and gets a response
    from the corresponding assistant. The assistant's response is also saved and sent.

    Args:
        update (telegram.Update): The incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing bot and user data.

    Returns:
        TALK_MESSAGE (str): Keeps the conversation ongoing in this state.

    Raises:
        OpenAIError: If the assistant fails to respond.
        BadRequest: If message formatting fails (e.g. HTML issue).
    """
    context.user_data["mode"] = None

    user_message = update.message.text

    # Connecting the assistant and DB
    openai_client: OpenAIClient = context.bot_data["openai_client"]
    thread_repository: GptThreadRepository = context.bot_data["thread_repository"]

    tg_user_id = update.effective_user.id
    mode = SessionMode.TALK.value

    thread_id = await thread_repository.get_thread_id(tg_user_id, mode)

    if thread_id is None:
        thread = await openai_client.create_thread()
        thread_id = thread.id
        await thread_repository.create_thread(tg_user_id, mode, thread_id)

    # Saving users message in DB
    await thread_repository.add_message(thread_id, role=MessageRole.USER.value, content=user_message)

    personality = context.user_data.get("personality", "einstein")
    attribute_name = f"ai_assistant_talk_{personality}_mileshkin_id"
    assistant_id = getattr(config, attribute_name)

    # Get response from assistant
    try:
        reply = await openai_client.ask(
            assistant_id=assistant_id,
            thread_id=thread_id,
            user_message=user_message
        )
    except OpenAIError as e:
        logger.warning(f"Assistant failed in /talk: {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return TALK_MESSAGE

    reply = sanitize_html(reply)

    # Saving assistants message in DB
    await thread_repository.add_message(thread_id, role=MessageRole.ASSISTANT.value, content=reply)

    # Sending the assistant's response to the user
    try:
        await send_html_message(update, context, reply)
    except BadRequest as e:
        logger.warning(f"Error sending HTML message in /talk: {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return TALK_MESSAGE

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="You can end the chat or ask the next question",
        reply_markup=get_end_chat_button()
    )
    return TALK_MESSAGE



async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ends the conversation and returns to the main menu via /start.

    Args:
        update (telegram.Update): The incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing bot and user data.

    Returns:
        Result of start(): main menu message.
    """
    await update.callback_query.answer()
    return await start(update, context)


"""
ConversationHandler for the TALK mode with historical personalities.

The assistant selected is based on the user's choice and is retrieved dynamically
from configuration using `getattr(config, ...)`.

Entry Points:
- /talk command initializes the conversation and shows personality buttons.

States:
- CHOOSE_PERSONALITY: Waits for personality selection.
- TALK_MESSAGE: Handles free-form user questions and returns assistant replies.

Fallbacks:
- /stop command or "End chat" button ends the session.
"""
talk_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("talk", choose_personality),
    ],
    states={
        CHOOSE_PERSONALITY: [
            CallbackQueryHandler(start_dialogue, pattern="^(einstein|napoleon|king|mercury)$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, choose_personality_warning)
        ],
        TALK_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_personality),
            CommandHandler("stop", end_chat),
            CallbackQueryHandler(end_chat, pattern="^end_chat$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(end_chat, pattern="^end_chat$"),
        CommandHandler("stop", end_chat)
    ]
)
