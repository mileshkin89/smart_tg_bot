from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler
)

from bot.commands import (
    start,
    random,
    gpt_conv_handler,
    voice_chat_intro,
    voice_handler,
    talk_conv_handler,
    quiz_conv_handler,
    translate_conv_handler
)

from db.initializer import DatabaseInitializer
from db.repository import GptSessionRepository
from services import OpenAIClient, SpeechToText
from settings.config import config


def main():
    db_initializer = DatabaseInitializer(config.path_to_db)
    db_initializer.create_tables()

    session_repository = GptSessionRepository(config.path_to_db)

    openai_client = OpenAIClient(
        openai_api_key=config.openai_api_key,
        model=config.openai_model,
        temperature=config.openai_model_temperature
    )

    app = ApplicationBuilder().token(config.tg_bot_api_key).build()

    app.bot_data["openai_client"] = openai_client
    app.bot_data["session_repository"] = session_repository

    speech_to_text = SpeechToText(credentials_path=config.path_to_google_credentials / "STT.json")
    app.bot_data["speech_to_text"] = speech_to_text

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("random", random))
    app.add_handler(CommandHandler("voice_chat", voice_chat_intro))

    app.add_handler(CallbackQueryHandler(start, pattern="^start$"))
    app.add_handler(CallbackQueryHandler(random, pattern="^random$"))

    app.add_handler(gpt_conv_handler)
    app.add_handler(voice_handler)
    app.add_handler(talk_conv_handler)
    app.add_handler(quiz_conv_handler)
    app.add_handler(translate_conv_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()