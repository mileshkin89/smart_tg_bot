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

    intro = await load_message("gpt")
    image_bytes = await load_image("gpt")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=intro)

    return GPT_MESSAGE



async def gpt_handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["mode"] = None

    user_message = update.message.text

    openai_client: OpenAIClient = context.bot_data["openai_client"]
    thread_repository: GptThreadRepository = context.bot_data["thread_repository"]

    tg_user_id = update.effective_user.id
    mode = SessionMode.GPT.value

    thread_id = await thread_repository.get_thread_id(tg_user_id, mode)

    if thread_id is None:
        thread = await openai_client.create_thread()
        thread_id = thread.id
        await thread_repository.create_thread(tg_user_id, mode, thread_id)

    await thread_repository.add_message(thread_id, role=MessageRole.USER.value, content=user_message)

    assistant_id = config.ai_assistant_gpt_mileshkin_id

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

    await thread_repository.add_message(thread_id, role=MessageRole.ASSISTANT.value, content=reply)

    try:
        await send_html_message(update=update, context=context,text=reply)
    except BadRequest as e:
        logger.warning(f"Error sending HTML message in /gpt: {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return GPT_MESSAGE

    return GPT_MESSAGE



async def gpt_end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await send_html_message(
        update=update,
        context=context,
        text="Chat ended. Type /gpt to start again.")

    return ConversationHandler.END



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
