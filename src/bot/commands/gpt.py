"""
This module implements a GPT-based assistant mode using Telegram's ConversationHandler.

The user interacts with the assistant via free-form text messages. The bot maintains
a persistent thread for each user in the OpenAI API and stores conversation history in a local SQLite database.

Features:
- Initializes a GPT chat mode with an introduction and image.
- Supports storing messages and threads in a database.
- Ensures thread continuity with OpenAI Assistant API.
- Handles assistant responses and gracefully manages errors.

Main Components:
- gpt_intro: Initializes GPT mode and shows the welcome message.
- gpt_handle_user_message: Handles conversation and message persistence.
- gpt_end_chat: Gracefully ends the GPT chat session.
- gpt_conv_handler: ConversationHandler managing the state transitions.
"""

from telegram import Update
from telegram.error import BadRequest
from openai import OpenAIError
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)
from db.repository import GptThreadRepository
from db.enums import SessionMode, MessageRole
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image
from bot.sanitize_html import sanitize_html
from services import OpenAIClient
from settings import config, get_logger


logger = get_logger(__name__)
GPT_MESSAGE = SessionMode.GPT.value


async def gpt_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /gpt command and prepares the bot for GPT chat mode.

    Sends the introductory message and image for GPT mode and activates it for the user.
    This enables the user to start chatting with the short-response assistant.

    Args:
        update (telegram.Update): The incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing bot and user data.

    Returns:
        GPT_MESSAGE (str): state of gpt_conv_handler

    Side Effects:
        - Sends the GPT welcome image and message.
        - Displays GPT-specific menu buttons.
    """
    intro = await load_message("gpt")
    image_bytes = await load_image("gpt")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=intro)

    return GPT_MESSAGE



async def gpt_handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles user messages in GPT mode.

    This function processes free-form text messages sent by the user when the GPT mode is active.
    It ensures that each user has a corresponding OpenAI thread and stores the conversation history.
    The assistant responses concisely, and all messages are saved to the local database.

    Args:
        update (telegram.Update): The incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing bot and user data.

    Raises:
        openai.OpenAIError: If the assistant fails to process the message or respond.
        telegram.error.BadRequest: Error sending message in Telegram

    Returns:
        GPT_MESSAGE (str): state of gpt_conv_handler

    Side Effects:
        - Sets context.user_data["mode"] to SessionMode.GPT.
        - Sends a message back to the user containing the assistant's reply.
        - Stores both the user message and assistant reply in the SQLite database.
        - Creates a new OpenAI thread if one doesn't exist for the current user and mode.
    """
    context.user_data["mode"] = None

    user_message = update.message.text

    # Connecting the assistant and DB
    openai_client: OpenAIClient = context.bot_data["openai_client"]
    thread_repository: GptThreadRepository = context.bot_data["thread_repository"]

    tg_user_id = update.effective_user.id
    mode = SessionMode.GPT.value

    thread_id = await thread_repository.get_thread_id(tg_user_id, mode)

    if thread_id is None:
        thread = await openai_client.create_thread()
        thread_id = thread.id
        await thread_repository.create_thread(tg_user_id, mode, thread_id)

    # Saving users message in DB
    await thread_repository.add_message(thread_id, role=MessageRole.USER.value, content=user_message)

    assistant_id = config.ai_assistant_gpt_mileshkin_id

    # Get response from assistant
    try:
        reply = await openai_client.ask(
            assistant_id=assistant_id,
            thread_id=thread_id,
            user_message=user_message
        )
    except OpenAIError as e:
        logger.warning(f"Assistant failed in /gpt: {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return GPT_MESSAGE

    reply = sanitize_html(reply)

    # Saving assistants message in DB
    await thread_repository.add_message(thread_id, role=MessageRole.ASSISTANT.value, content=reply)

    # Sending the assistant's response to the user
    try:
        await send_html_message(update=update, context=context,text=reply)
    except BadRequest as e:
        logger.warning(f"Error sending HTML message in /gpt: {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return GPT_MESSAGE

    return GPT_MESSAGE



async def gpt_end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /stop command and ends the chat.

    Args:
        update (telegram.Update): The incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing bot and user data.

    Returns:
        ConversationHandler.END: terminates the gpt_conv_handler

    Side Effects:
        - Sends a message to the user that the chat is over.
    """

    await send_html_message(
        update=update,
        context=context,
        text="Chat ended. Type /gpt to start again.")

    return ConversationHandler.END


"""
ConversationHandler that manages the GPT chat interaction.

Entry Points:
- /gpt command triggers the chat initialization.

States:
- GPT_MESSAGE: Handles incoming user messages and sends them to the GPT assistant.

Fallbacks:
- /stop command ends the conversation and resets the state.
"""
gpt_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("gpt", gpt_intro)],
    states={
        GPT_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_handle_user_message),
            CommandHandler("stop", gpt_end_chat)
        ]
    },
    fallbacks=[CommandHandler("stop", gpt_end_chat)]
)
