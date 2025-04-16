from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
import uuid
from pathlib import Path
import os
from bot.audio_converter_stt import  convert_audio_for_stt
from bot.resource_loader import load_message, load_image
from bot.message_sender import send_html_message, send_image_bytes
from settings import config, get_logger
from services import OpenAIClient, SpeechToText, TextToSpeech


async def voice_chat_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):

    intro = await load_message("voice_chat")
    image_bytes = await load_image("voice_chat")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=intro)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    voice = update.message.voice
    print("Получил аудио в ТГ")

    # Receiving a file from Telegram
    input_file = await context.bot.get_file(voice.file_id)
    print("Получил аудио с ТГ в инпут")

    # Generate a unique name for the file
    unique_id = uuid.uuid4().hex
    input_path: Path = config.path_to_input_audio_file / f"{unique_id}.ogg"
    print("Присвоил аудио с инпут уникальное имя")

    # Save the file in storage/input/
    await input_file.download_to_drive(input_path)
    print(f"Voice file saved to: {input_path}")
    print("Сохранил аудиос уникальным именем в инпут")

    try:
        converted_path = convert_audio_for_stt(input_path)
        print(f"Converted file saved at: {converted_path}")

        speech_to_text: SpeechToText = context.bot_data["speech_to_text"]
        text = speech_to_text.recognize(converted_path)

        if text:
            await update.message.reply_text(f"🗣️ You said: {text}")
        else:
            await update.message.reply_text("⚠️ Sorry, I couldn't recognize any speech.")
    finally:
        # Deleting files after processing
        for file in [input_path, converted_path]:
            try:
                os.remove(file)
                print(f"Deleted file: {file}")
            except Exception as e:
                print(f"Failed to delete {file}: {e}")







    #
    # # Отправка текста в ChatGPT
    # openai_client: OpenAIClient = context.bot_data["openai_client"]
    #
    # prompt = await load_prompt("voice_chat")
    # response_text = await openai_client.ask(user_message=text, system_prompt=prompt)
    #
    #
    # # Преобразование ответа в голос
    # text_to_speech = context.bot_data["text_to_speech"]  # Должен быть объект TextToSpeech
    # audio_bytes = await text_to_speech.synthesize(response_text)
    #
    # if not audio_bytes:
    #     await update.message.reply_text("⚠️ Text-to-speech error.")
    #     return
    #
    #
    # # Отправка голосового ответа
    # await update.message.reply_voice(voice=audio_bytes)



voice_handler = MessageHandler(filters.VOICE, handle_voice_message)

