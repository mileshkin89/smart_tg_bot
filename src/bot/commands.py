from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from bot.keyboards import get_main_menu_button
from bot.message_sender import send_html_message, send_image_bytes, show_menu
from bot.resource_loader import load_message, load_image, load_menu, load_prompt
from db.repository import GptSessionRepository
from services import OpenAIClient


AWAITING_USER_MESSAGE = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = await load_message("main")
    image_bytes = await load_image("main")
    menu_commands = await load_menu("main")

    await send_image_bytes(
        update=update,
        context=context,
        image_bytes=image_bytes,
    )

    await send_html_message(
        update=update,
        context=context,
        text=text,
    )

    await show_menu(
        update=update,
        context=context,
        commands=menu_commands
    )


async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):

    prompt = await load_prompt("random")
    intro = await load_message("random")
    image_bytes = await load_image("random")

    openai_client: OpenAIClient = context.bot_data["openai_client"]
    session_repository: GptSessionRepository = context.bot_data["session_repository"]

    reply = await openai_client.ask(
        user_message="Give me a random interesting technical fact.",
        system_prompt=prompt
    )

    combined = f"{intro}\n\n{reply}"

    await send_image_bytes(
        update=update,
        context=context,
        image_bytes=image_bytes,
    )

    await send_html_message(
        update=update,
        context=context,
        text=combined,
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Choose your next step:",
        reply_markup=get_main_menu_button()
    )


async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    prompt = await load_prompt("gpt")
    intro = await load_message("gpt")
    image_bytes = await load_image("gpt")

    openai_client: OpenAIClient = context.bot_data["openai_client"]

    await send_image_bytes(
        update=update,
        context=context,
        image_bytes=image_bytes
    )

    await send_html_message(
        update=update,
        context=context,
        text=intro
    )

    context.user_data["system_prompt"] = prompt

    return AWAITING_USER_MESSAGE


async def gpt_handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    openai_client: OpenAIClient = context.bot_data["openai_client"]
    system_prompt = context.user_data.get("system_prompt", "")

    reply = await openai_client.ask(
        user_message=user_message,
        system_prompt=system_prompt
    )

    await send_html_message(
        update=update,
        context=context,
        text=reply
    )

    return AWAITING_USER_MESSAGE

# Переделать на кнупки:
async def gpt_end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершает диалог по команде /stop."""
    await send_html_message(
        update=update,
        context=context,
        text="Chat ended. Type /gpt to start again.")

    return ConversationHandler.END


gpt_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("gpt", gpt)],
    states={
        AWAITING_USER_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_handle_user_message),
            CommandHandler("stop", gpt_end_chat)  # Позволяет выйти из чата командой /stop
        ]
    },
    fallbacks=[CommandHandler("stop", gpt_end_chat)]
)
