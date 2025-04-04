from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image, load_prompt
from services import OpenAIClient
import re
from .start import start
from bot.keyboards import get_quiz_choose_topic_button, get_quiz_menu_button

from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler
)

QUIZ_MESSAGE = "QUIZ"


def parse_quiz_question(text: str):
    """
    Парсит вопрос и варианты ответов из ответа ChatGPT.
    Ожидаемый формат:

    Question: <текст вопроса>

    A) <вариант 1>
    B) <вариант 2>
    C) <вариант 3>
    D) <вариант 4>

    Correct Answer: <буква (A, B, C, D)>
    """
    question_match = re.search(r"Question:\s*(.+)", text, re.IGNORECASE)
    options_match = re.findall(r"([A-D])\)\s*(.+)", text)
    correct_answer_match = re.search(r"Correct Answer:\s*([A-D])", text, re.IGNORECASE)

    if not question_match or len(options_match) != 4 or not correct_answer_match:
        raise ValueError("Response format is incorrect or missing elements.")

    question = question_match.group(1).strip()
    options = {key: value.strip() for key, value in options_match}
    correct_answer_letter = correct_answer_match.group(1).strip()

    return question, options, correct_answer_letter


def update_quiz_score(context: ContextTypes.DEFAULT_TYPE, user_id: int, user_answer: str) -> tuple[bool, int]:

    correct_answer = context.user_data.get("correct_answer", "")

    if "quiz_scores" not in context.user_data:
        context.user_data["quiz_scores"] = {}

    # Если пользователь новый или начал новый квиз, сбрасываем счётчик
    if user_id not in context.user_data["quiz_scores"]:
        context.user_data["quiz_scores"][user_id] = 0

    # Проверяем правильность ответа
    is_correct = user_answer == correct_answer

    # Увеличиваем счётчик при правильном ответе
    if is_correct:
        context.user_data["quiz_scores"][user_id] += 1

    return is_correct, context.user_data["quiz_scores"][user_id]


async def choose_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):

    intro = await load_message("quiz")
    image_bytes = await load_image("quiz")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=intro)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="What topic do you want to get the first question about?",
        reply_markup=get_quiz_choose_topic_button()
    )

    return QUIZ_MESSAGE


async def get_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    quiz_topic = query.data

    await query.answer()

    if quiz_topic == "next_question_quiz":
        quiz_topic = context.user_data.get("quiz_topic", None)
    else:
        context.user_data["quiz_topic"] = quiz_topic

    if not quiz_topic:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Ошибка: тема викторины не найдена. Пожалуйста, выберите тему снова."
        )
        return QUIZ_MESSAGE


    user_message = f"Generate an interesting mid-level question on the topic: {quiz_topic}"
    system_prompt = await load_prompt("quiz")

    openai_client: OpenAIClient = context.bot_data["openai_client"]

    reply = await openai_client.ask(
        user_message=user_message,
        system_prompt=system_prompt
    )

    print(f"🔍 OpenAI response:\n{reply}")
    print(f"Выбранная тема {quiz_topic}")


    try:
        question, options, correct_answer = parse_quiz_question(reply)
    except ValueError as e:
        print(f"❌ Ошибка парсинга: {e}")
        print(f"🔍 Ответ от OpenAI:\n{reply}")  # Логируем весь ответ
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ Ошибка обработки вопроса. Попробуйте ещё раз.\n\n(Лог: {e})"
        )
        return


    context.user_data["correct_answer"] = correct_answer  # Сохраняем правильный ответ

    keyboard = [[InlineKeyboardButton(f"{key}) {value}", callback_data=key)] for key, value in options.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Selected topic: {quiz_topic.capitalize()}\n\n{question}"

    await send_html_message(
        update=update,
        context=context,
        text=text
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Choose your answer:",
        reply_markup=reply_markup
    )

    return QUIZ_MESSAGE


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user_answer = query.data

    await query.answer()

    # Проверяем, правильный ли ответ, и получаем счётчик
    is_correct, total_correct = update_quiz_score(context, user_id, user_answer)

    # Формируем сообщение о результате
    result_text = "✅ Correct!" if is_correct else f"❌ Wrong! The correct answer was: {context.user_data['correct_answer']}"
    score_text = f"Your total correct answers: {total_correct}"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{result_text}\n\n{score_text}",
        reply_markup=get_quiz_menu_button()  # Кнопки: следующий вопрос, сменить тему, завершить
    )

    return QUIZ_MESSAGE


async def next_question_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["quiz_topic"] = context.user_data.get("quiz_topic", "science")

    return await get_question(update, context)


async def change_topic_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    return await choose_topic(update, context)


async def end_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    return await start(update, context)



quiz_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("quiz", choose_topic)
    ],
    states={
        QUIZ_MESSAGE: [
            CallbackQueryHandler(get_question, pattern="^(science|sport|art|cinema)$"),
            CallbackQueryHandler(handle_answer, pattern="^[ABCD]$"), #CallbackQueryHandler(get_question, pattern="^A|B|C|D$"),
            CallbackQueryHandler(next_question_quiz, pattern="^next_question_quiz$"),
            CallbackQueryHandler(change_topic_quiz, pattern="^change_topic_quiz$"),
            CallbackQueryHandler(end_quiz, pattern="^end_quiz$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(end_quiz, pattern="^(start)$"),
        CallbackQueryHandler(next_question_quiz, pattern="^(get_question)$"),
        CallbackQueryHandler(change_topic_quiz, pattern="^(choose_topic)$")
    ]
)