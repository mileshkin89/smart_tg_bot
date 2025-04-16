from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from db.initializer import DatabaseInitializer
from db.repository import GptThreadRepository
from services import OpenAIClient, SpeechToText
from settings.config import config
from bot.commands import (
    start,
    random,
    gpt_conv_handler,
    talk_conv_handler,
    quiz_conv_handler,
    translate_conv_handler,
    resume_handler,
    voice_chat_intro,
    voice_handler
)


def main():
    """
    Starts the Telegram bot application.

    This function initializes the local SQLite database, sets up the OpenAI client,
    registers command and conversation handlers for the Telegram bot, and starts polling updates.

    Handlers:
       - /start: Initializes the bot interface.
       - /random: Triggers the assistant to return a random technical fact.
       - CallbackQueryHandler: Supports menu button interactions for "start" and "random".
       - ConversationHandler:
         -- gpt_conv_handler: Handles free-form text input when in GPT mode.
         -- talk_conv_handler: Handles free-form text input when in TALK mode.
         -- quiz_conv_handler: Handles question-answer interaction when in QUIZ mode.
         -- translate_conv_handler: Handles free-form text input when in TRANSLATE mode.
         -- resume_handler: Handles user data collection and resume file creation when in RESUME mode

    Environment:
       Requires the following values from the config:
           - OpenAI API key and model settings
           - Telegram bot token
           - Path to SQLite database
    """

    db_initializer = DatabaseInitializer(config.path_to_db)
    db_initializer.create_tables()

    thread_repository = GptThreadRepository(config.path_to_db)

    openai_client = OpenAIClient(
        openai_api_key=config.openai_api_key,
        model=config.openai_model,
        temperature=config.openai_model_temperature
    )

    speech_to_text = SpeechToText()

    app = ApplicationBuilder().token(config.tg_bot_api_key).build()

    app.bot_data["openai_client"] = openai_client
    app.bot_data["thread_repository"] = thread_repository

    app.bot_data["speech_to_text"] = speech_to_text

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("random", random))
    app.add_handler(CommandHandler("voice_chat", voice_chat_intro))

    app.add_handler(CallbackQueryHandler(start, pattern="^start$"))
    app.add_handler(CallbackQueryHandler(random, pattern="^random$"))

    app.add_handler(gpt_conv_handler)
    app.add_handler(talk_conv_handler)
    app.add_handler(quiz_conv_handler)
    app.add_handler(translate_conv_handler)
    app.add_handler(resume_handler)
    app.add_handler(voice_handler)


    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()