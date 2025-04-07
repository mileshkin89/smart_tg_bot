from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from openai import OpenAIError

from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image
from bot.keyboards import get_random_menu_button
from bot.sanitize_html import sanitize_html
from db.repository import GptThreadRepository
from db.enums import SessionMode, MessageRole
from services import OpenAIClient
from settings import config, get_logger

logger = get_logger(__name__)


async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["mode"] = None

    intro = await load_message("random")
    image_bytes = await load_image("random")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)

    openai_client: OpenAIClient = context.bot_data["openai_client"]
    thread_repository: GptThreadRepository = context.bot_data["thread_repository"]

    tg_user_id = update.effective_user.id
    mode = SessionMode.RANDOM.value

    thread_id = await thread_repository.get_thread_id(tg_user_id, mode)

    if thread_id is None:
        thread = await openai_client.create_thread()
        thread_id = thread.id
        await thread_repository.create_thread(tg_user_id, mode, thread_id)

    user_message = "Give me a random interesting technical fact."

    await thread_repository.add_message(thread_id, role=MessageRole.USER.value, content=user_message)

    assistant_id = config.ai_assistant_random_mileshkin_id

    try:
        reply = await openai_client.ask(
            assistant_id=assistant_id,
            thread_id=thread_id,
            user_message=user_message
        )
    except OpenAIError as e:
        logger.warning(f"Assistant failed in /random: {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return

    reply = sanitize_html(reply)

    await thread_repository.add_message(thread_id, role=MessageRole.ASSISTANT.value, content=reply)

    combined = f"{intro}\n\n{reply}"

    try:
        await send_html_message(update=update, context=context, text=combined)
    except BadRequest as e:
        logger.warning(f"Error sending HTML message in /random: {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Choose your next step:",
        reply_markup=get_random_menu_button()
    )