from telegram import Update
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image, load_prompt
from .start import start
from bot.sanitize_html import sanitize_html

from services import OpenAIClient


from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from bot.keyboards import get_talk_menu_button, get_end_chat_button


TALK_MESSAGE = "TALK"

async def choose_personality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает пользователю меню выбора личности."""

    intro = await load_message("talk")
    image_bytes = await load_image("talk")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=intro)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Who would you like to ask a question?",
        reply_markup=get_talk_menu_button()
    )



async def start_dialogue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор личности и запускает режим диалога."""
    query = update.callback_query
    personality = query.data

    prompt = await load_prompt(f"{personality}")

    context.user_data["personality"] = personality
    context.user_data["system_prompt"] = prompt

    await query.answer()
    await send_html_message(update, context, f"You chose {personality.capitalize()}. Start a conversation!")

    return TALK_MESSAGE


async def chat_with_personality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает в стиле выбранной личности."""
    user_message = update.message.text
    system_prompt = context.user_data.get("system_prompt", "")
    openai_client: OpenAIClient = context.bot_data["openai_client"]

    reply = await openai_client.ask(user_message=user_message, system_prompt=system_prompt)
    reply = sanitize_html(reply)

    await send_html_message(update, context, reply)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="You can end the chat or ask the next question",
        reply_markup=get_end_chat_button()
    )

    return TALK_MESSAGE


# async def button_end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Завершает чат и возвращает пользователя в главное меню."""
#     query = update.callback_query
#     await query.answer()
#     #await update.callback_query.message.reply_text("Chat ended.")
#
#     return await start(update, context)


async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершает чат и отправляет пользователя в главное меню"""
    await update.callback_query.answer()  # Закрыть уведомление о нажатии кнопки
    #await update.callback_query.message.reply_text("Chat ended.")


    return await start(update, context)


talk_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("talk", choose_personality),
        CallbackQueryHandler(start_dialogue, pattern="^(einstein|napoleon|king|mercury)$")
    ],
    states={
        TALK_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_personality),
            CommandHandler("stop", end_chat),
            CallbackQueryHandler(end_chat, pattern="^end_chat$")
            #CallbackQueryHandler(button_end_chat, pattern="^end_chat$")
        ]
    },
    fallbacks=[CallbackQueryHandler(end_chat, pattern="^end_chat$")#CommandHandler("stop", end_chat)
               ]
)
