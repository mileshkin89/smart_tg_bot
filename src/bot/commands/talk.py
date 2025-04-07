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

    await send_html_message(update, context, "Please choose a personality from the buttons before starting the conversation.")
    return CHOOSE_PERSONALITY



async def start_dialogue(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    personality = query.data

    context.user_data["personality"] = personality

    await query.answer()
    await send_html_message(update, context, f"You chose {personality.capitalize()}. Start a conversation!")

    return TALK_MESSAGE



async def chat_with_personality(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["mode"] = None

    user_message = update.message.text

    openai_client: OpenAIClient = context.bot_data["openai_client"]
    thread_repository: GptThreadRepository = context.bot_data["thread_repository"]

    tg_user_id = update.effective_user.id
    mode = SessionMode.TALK.value

    thread_id = await thread_repository.get_thread_id(tg_user_id, mode)

    if thread_id is None:
        thread = await openai_client.create_thread()
        thread_id = thread.id
        await thread_repository.create_thread(tg_user_id, mode, thread_id)

    await thread_repository.add_message(thread_id, role=MessageRole.USER.value, content=user_message)

    personality = context.user_data.get("personality", "einstein")
    attribute_name = f"ai_assistant_talk_{personality}_mileshkin_id"
    assistant_id = getattr(config, attribute_name)

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

    await thread_repository.add_message(thread_id, role=MessageRole.ASSISTANT.value, content=reply)

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
    await update.callback_query.answer()

    return await start(update, context)



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
