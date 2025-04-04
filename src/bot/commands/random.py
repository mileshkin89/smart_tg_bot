from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image, load_prompt
from db.repository import GptSessionRepository
from services import OpenAIClient
from bot.keyboards import get_random_menu_button
from bot.sanitize_html import sanitize_html


async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):

    prompt = await load_prompt("random")
    intro = await load_message("random")
    image_bytes = await load_image("random")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)

    openai_client: OpenAIClient = context.bot_data["openai_client"]
    session_repository: GptSessionRepository = context.bot_data["session_repository"]

    reply = await openai_client.ask(
        user_message="Give me a random interesting technical fact.",
        system_prompt=prompt
    )
    print(f"before sanitize:\n{reply}")
    reply = sanitize_html(reply)
    print(f"after sanitize:\n{reply}")

    combined = f"{intro}\n\n{reply}"

    try:
        await send_html_message(update=update, context=context, text=combined)
    except BadRequest as e:
        print(f"Error sending HTML message: {e}")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Choose your next step:",
        reply_markup=get_random_menu_button()
    )