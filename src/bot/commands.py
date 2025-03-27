from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from bot.keyboards import get_main_menu_button, get_random_menu_button, get_talk_menu_button
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
        reply_markup=get_random_menu_button()
    )


# /gpt
#=====================================================================================================


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


# /talk
#=====================================================================================================

async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает пользователю меню выбора личности."""

    intro = await load_message("talk")
    image_bytes = await load_image("talk")

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

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Who would you like to ask a question?",
        reply_markup=get_talk_menu_button()
    )



async def start_dialogue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор личности и запускает режим диалога."""
    query = update.callback_query
    personality = query.data  # Получаем выбор пользователя

    prompt = await load_prompt(f"{personality}")

    # if personality not in PERSONALITY_PROMPTS:
    #     await query.answer("Некорректный выбор.")
    #     return ConversationHandler.END

    context.user_data["personality"] = personality  # Запоминаем личность
    context.user_data["system_prompt"] = prompt

    await query.answer()
    await send_html_message(update, context, f"Ты выбрал {personality.capitalize()}. Начинай разговор!")

    return AWAITING_USER_MESSAGE  # Переводим в режим чата


async def chat_with_personality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает в стиле выбранной личности."""
    user_message = update.message.text
    system_prompt = context.user_data.get("system_prompt", "")
    openai_client: OpenAIClient = context.bot_data["openai_client"]

    reply = await openai_client.ask(user_message=user_message, system_prompt=system_prompt)
    await send_html_message(update, context, reply)

    return AWAITING_USER_MESSAGE  # Оставляем пользователя в чате


async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершает диалог и возвращает пользователя в главное меню."""
    await send_html_message(update, context, "Диалог завершен. Возвращаю в главное меню.")
    return ConversationHandler.END


talk_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("talk", talk),
        CallbackQueryHandler(start_dialogue, pattern="^(einstein|napoleon|king|mercury)$")
    ],
    states={
        AWAITING_USER_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_personality),
            CommandHandler("stop", end_chat)
        ]
    },
    fallbacks=[CommandHandler("stop", end_chat)]
)
