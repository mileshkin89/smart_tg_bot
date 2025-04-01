from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from bot.resource_loader import load_message, load_image, load_prompt
from bot.message_sender import send_html_message, send_image_bytes
from services import OpenAIClient, SpeechToText, TextToSpeech


async def voice_chat_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):

    intro = await load_message("voice_chat")
    image_bytes = await load_image("voice_chat")

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


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    file_path = file.file_path


    # Преобразование голосового сообщения в текст
    speech_to_text = context.bot_data["speech_to_text"]  # Должен быть объект SpeechToText
    text = await speech_to_text.recognize(file_path)

    if not text:
        await update.message.reply_text("⚠️ The voice message could not be recognized. Please try again.")
        return


    # Отправка текста в ChatGPT
    openai_client: OpenAIClient = context.bot_data["openai_client"]

    prompt = await load_prompt("voice_chat")
    response_text = await openai_client.ask(user_message=text, system_prompt=prompt)


    # Преобразование ответа в голос
    text_to_speech = context.bot_data["text_to_speech"]  # Должен быть объект TextToSpeech
    audio_bytes = await text_to_speech.synthesize(response_text)

    if not audio_bytes:
        await update.message.reply_text("⚠️ Text-to-speech error.")
        return


    # Отправка голосового ответа
    await update.message.reply_voice(voice=audio_bytes)



voice_handler = MessageHandler(filters.VOICE, voice_chat_intro)

