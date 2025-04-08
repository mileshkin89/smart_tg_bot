from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from openai import OpenAIError
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler
)
import re
from bot.keyboards import get_quiz_choose_topic_button, get_quiz_menu_button
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image
from db.repository import GptThreadRepository
from db.enums import SessionMode, MessageRole
from services import OpenAIClient
from settings import config, get_logger
from .start import start


logger = get_logger(__name__)
QUIZ_MESSAGE = SessionMode.QUIZ.value


def parse_quiz_question(text: str):
    """
    Parses the question and answer options from the ChatGPT answer.
    Expected format:

    Question: <question text>

    A) <option 1>
    B) <option 2>
    C) <option 3>
    D) <option 4>

    Correct Answer: <letter (A, B, C, D)>
    """
    question_match = re.search(r"Question:\s*(.+)", text, re.IGNORECASE)
    options_match = re.findall(r"([A-D])\)\s*(.+)", text)
    correct_answer_match = re.search(r"Correct Answer:\s*([A-D])", text, re.IGNORECASE)

    if not question_match or len(options_match) != 4 or not correct_answer_match:
        logger.warning(f"\quiz, parse_quiz_question(). Response format is incorrect or missing elements.")
        raise ValueError("\quiz, parse_quiz_question(). Response format is incorrect or missing elements.")

    question = question_match.group(1).strip()
    options = {key: value.strip() for key, value in options_match}
    correct_answer_letter = correct_answer_match.group(1).strip()

    return question, options, correct_answer_letter


def update_quiz_score(context: ContextTypes.DEFAULT_TYPE, user_id: int, user_answer: str) -> tuple[bool, int]:

    correct_answer = context.user_data.get("correct_answer", "")

    if "quiz_scores" not in context.user_data:
        context.user_data["quiz_scores"] = {}

    # If the user is new or has started a new quiz, we reset the counter
    if user_id not in context.user_data["quiz_scores"]:
        context.user_data["quiz_scores"][user_id] = 0

    is_correct = user_answer == correct_answer

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

    context.user_data["mode"] = None
    query = update.callback_query
    quiz_topic = query.data

    await query.answer()

    # Check if the quiz topic has been selected earlier
    if quiz_topic == "next_question_quiz":
        quiz_topic = context.user_data.get("quiz_topic", None)
    else:
        context.user_data["quiz_topic"] = quiz_topic

    if not quiz_topic:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Quiz topic not found. Please select topic again."
        )
        return QUIZ_MESSAGE


    # Connecting the assistant and DB
    openai_client: OpenAIClient = context.bot_data["openai_client"]
    assistant_id = config.ai_assistant_quiz_mileshkin_id
    thread_repository: GptThreadRepository = context.bot_data["thread_repository"]

    tg_user_id = update.effective_user.id
    mode = SessionMode.QUIZ.value

    thread_id = await thread_repository.get_thread_id(tg_user_id, mode)

    if thread_id is None:
        thread = await openai_client.create_thread()
        thread_id = thread.id
        await thread_repository.create_thread(tg_user_id, mode, thread_id)


    user_message = f"Generate an interesting mid-level question on the topic: {quiz_topic}"

    # Get question from assistant
    try:
        reply = await openai_client.ask(
            assistant_id=assistant_id,
            thread_id=thread_id,
            user_message=user_message
        )
    except OpenAIError as e:
        logger.warning(f"Assistant failed to respond in /quiz, get_question(): {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return QUIZ_MESSAGE


    # Parse the question
    try:
        question, options, correct_answer = parse_quiz_question(reply)
    except ValueError as e:
        logger.warning(f"\quiz, get_question(). OpenAI response is incorrect. Parsing error: {e}\nResponse from OpenAI:\n{reply}")
        print(f"❌ Parsing error: {e}")
        print(f"🔍 Response from OpenAI:\n{reply}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ Error processing question. Try again.\n\n{e}"
        )
        return QUIZ_MESSAGE


    # Save the question, options and correct answer in DB
    await thread_repository.add_message(
        thread_id,
        role=MessageRole.ASSISTANT.value,
        content=f"question = {question},\noptions = {options},\ncorrect_answer = {correct_answer}"
    )

    context.user_data["correct_answer"] = correct_answer

    # Create buttons with answer options
    keyboard = [[InlineKeyboardButton(f"{key}) {value}", callback_data=key)] for key, value in options.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Selected topic:  {quiz_topic.capitalize()}\n\n{question}"

    await send_html_message(update, context, text)

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

    # Check if the answer is correct and get a counter
    is_correct, total_correct = update_quiz_score(context, user_id, user_answer)

    result_text = "✅ Correct!" if is_correct else f"❌ Wrong! The correct answer was: {context.user_data['correct_answer']}"
    score_text = f"Your total correct answers: {total_correct}"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{result_text}\n\n{score_text}",
        reply_markup=get_quiz_menu_button()
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
            CallbackQueryHandler(handle_answer, pattern="^[ABCD]$"),
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