from telegram import Update
from telegram.error import BadRequest
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image, load_prompt
from services import OpenAIClient
from bot.sanitize_html import sanitize_html

from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)


GPT_MESSAGE = "GPT"


async def gpt_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):

    prompt = await load_prompt("gpt")
    intro = await load_message("gpt")
    image_bytes = await load_image("gpt")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=intro)

    context.user_data["system_prompt"] = prompt

    return GPT_MESSAGE


async def gpt_handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    openai_client: OpenAIClient = context.bot_data["openai_client"]
    system_prompt = context.user_data.get("system_prompt", "")

    reply = await openai_client.ask(
        user_message=user_message,
        system_prompt=system_prompt
    )
    reply = sanitize_html(reply)

    try:
        await send_html_message(update=update, context=context,text=reply)
    except BadRequest as e:
        print(f"Error sending HTML message: {e}")

    return GPT_MESSAGE

# Переделать на кнупки:
async def gpt_end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершает диалог по команде /stop."""
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
            CommandHandler("stop", gpt_end_chat)  # Позволяет выйти из чата командой /stop
        ]
    },
    fallbacks=[CommandHandler("stop", gpt_end_chat)]
)
