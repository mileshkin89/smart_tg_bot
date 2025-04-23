"""
This module implements the voice chat functionality.

It allows the user to send a voice message, which is:
1. Converted to the appropriate format using FFmpeg.
2. Transcribed to text using Google Speech-to-Text.
3. Sent to OpenAI Assistant for a response.
4. Returned as text and synthesized voice via Google Text-to-Speech.

Main Components:
- voice_chat_intro: Sends intro image and instruction.
- handle_voice_message: Full processing pipeline for voice interaction.
- voice_handler: Telegram MessageHandler for incoming voice messages.
"""

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from openai import OpenAIError
import uuid
from pathlib import Path
import os
from bot.audio_converter_stt import  convert_audio_for_stt
from bot.resource_loader import load_message, load_image
from bot.message_sender import send_html_message, send_image_bytes
from bot.sanitize_html import sanitize_html
from db.repository import GptThreadRepository
from db.enums import SessionMode, MessageRole
from settings import config, get_logger
from services import OpenAIClient, SpeechToText, TextToSpeech


logger = get_logger(__name__)
VOICE_CHAT = SessionMode.VOICE_CHAT.value


async def voice_chat_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends the introductory message and image for voice chat mode.

    Args:
        update (telegram.Update): Incoming update with /voice_chat command.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Bot context with user data.

    Side Effects:
        - Sends image and HTML message with voice chat instructions.
    """

    intro = await load_message("voice_chat")
    image_bytes = await load_image("voice_chat")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=intro)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles incoming voice messages and initiates full voice-to-voice conversation.

    Workflow:
        - Downloads the user's voice message and saves it to input_audio/ folder.
        - Converts it using FFmpeg and saves to converted_audio/ folder.
        - Transcribes it with Google Speech-to-Text.
        - Sends transcription to OpenAI Assistant and receives response.
        - Sends text reply to user.
        - Synthesizes assistant reply to voice and sends as audio message.
        - Cleans up all temporary audio files.

    Args:
        update (telegram.Update): Update containing the voice message.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context with bot and user data.

    Raises:
        OpenAIError: If OpenAI fails to respond.

    Side Effects:
        - Saves and deletes audio files in `storage/`.
        - Sends messages and voice responses to the user.
        - Updates thread and message history in the database.
    """

    context.user_data["mode"] = None

    voice = update.message.voice
    input_file = await context.bot.get_file(voice.file_id)

    # Generate a unique name for the file
    unique_id = uuid.uuid4().hex
    config.path_to_input_audio_file.mkdir(parents=True, exist_ok=True)
    input_path: Path = config.path_to_input_audio_file / f"{unique_id}.ogg"

    # Save the file in storage/input_audio/.ogg
    await input_file.download_to_drive(input_path)


    # The file is converted to the required format. The text is recognized.
    try:
        # Save converted file in storage/convert_audio/.ogg
        converted_path = convert_audio_for_stt(input_path)
        logger.info(f"Save converted file in {converted_path}")

        speech_to_text: SpeechToText = context.bot_data["speech_to_text"]
        text = await speech_to_text.recognize(converted_path)

        if text:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🗣️ You said: {text}",
                reply_to_message_id=update.message.message_id
            )
        else:
            await update.message.reply_text("⚠️ Sorry, I couldn't recognize any speech.")
    finally:
        # Deleting files after processing
        for file in [input_path, converted_path]:
            try:
                os.remove(file)
                logger.info(f"Deleted file in {file}")
            except Exception as e:
                logger.warning(f"Failed to delete {file}: {e}")


    # Connecting the assistant and DB
    openai_client: OpenAIClient = context.bot_data["openai_client"]
    assistant_id = config.ai_assistant_voice_chat_mileshkin_id
    thread_repository: GptThreadRepository = context.bot_data["thread_repository"]

    tg_user_id = update.effective_user.id
    mode = SessionMode.VOICE_CHAT.value

    thread_id = await thread_repository.get_thread_id(tg_user_id, mode)

    if thread_id is None:
        thread = await openai_client.create_thread()
        thread_id = thread.id
        await thread_repository.create_thread(tg_user_id, mode, thread_id)


    # Saving users message in DB
    await thread_repository.add_message(thread_id, role=MessageRole.USER.value, content=text)

    user_message = f"Answer the following question in English: {text}"

    # Get response from assistant
    try:
        reply = await openai_client.ask(
            assistant_id=assistant_id,
            thread_id=thread_id,
            user_message=user_message
        )
    except OpenAIError as e:
        logger.warning(f"Assistant failed to respond in /voice_chat, handle_voice_message(): {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return

    reply = sanitize_html(reply)

    if len(reply) > 1000 or any(bad in reply for bad in ["<?", "</", "{%", ">>>", "==", "***", "<script", "###"]):
        logger.warning("Abnormal model output")
        await thread_repository.add_message(thread_id, role=MessageRole.ASSISTANT.value, content=reply)
        reply = "Sorry, something went wrong. Please rephrase your question and try again."
    else:
        await thread_repository.add_message(thread_id, role=MessageRole.ASSISTANT.value, content=reply)

    await update.message.reply_text(f"🗣️ My answer: {reply}")


    # Converting text response to voice
    try:
        text_to_speech: TextToSpeech = context.bot_data["text_to_speech"]
        # Synthesized audio file saved in storage/stt_audio/.ogg
        audio_bytes = await text_to_speech.synthesize(reply)
        logger.info(f"Synthesized audio file saved in {audio_bytes}")

        if audio_bytes:
            await update.message.reply_voice(voice=audio_bytes)
        else:
            await update.message.reply_text("⚠️ Text-to-speech error.")
            return
    finally:
        # Deleting files after processing
        for file in [audio_bytes]:
            try:
                os.remove(file)
            except Exception as e:
                logger.warning(f"Failed to delete {file}: {e}")


"""
MessageHandler for handling incoming Telegram voice messages in voice chat mode.

Trigger:
    - Any VOICE message sent by the user.

Callback:
    - handle_voice_message
"""
voice_handler = MessageHandler(filters.VOICE, handle_voice_message)

