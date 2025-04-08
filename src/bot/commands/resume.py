from telegram import Update
from telegram.error import BadRequest
from openai import OpenAIError
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image
from bot.keyboards import get_resume_button, get_resume_format_file_button, get_resume_format_file_button_end
from bot.sanitize_html import sanitize_html
from bot.file_converter import convert_to_file
from db.repository import GptThreadRepository
from db.enums import SessionMode, MessageRole
from services import OpenAIClient
from settings import config, get_logger
from .start import start


POSITION = "POSITION"
NAME = "NAME"
CONTACTS = "CONTACTS"
EDUCATION = "EDUCATION"
WORK_EXPERIENCE = "WORK EXPERIENCE"
SKILLS = "SKILLS"
ADDITIONAL_INFORMATION = "ADDITIONAL INFORMATION"
CONFIRM = "CONFIRM"
FORMAT_FILE = SessionMode.RESUME.value

logger = get_logger(__name__)


async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE):

    intro = await load_message("resume")
    image_bytes = await load_image("resume")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=f"{intro}")
    await send_html_message(update=update, context=context, text=f"\n\nWrite what <b>position</b> you are applying for:")

    return POSITION


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["position"] = update.message.text
    await send_html_message(update=update, context=context, text="Enter your <b>full name</b>:")

    return NAME


async def get_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["name"] = update.message.text
    await send_html_message(update=update, context=context, text="Enter your <b>contact information</b> (phone, email, Linkedin):")

    return CONTACTS


async def get_education(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["contacts"] = update.message.text
    await send_html_message(update=update, context=context, text="Describe your <b>education</b>:")

    return EDUCATION


async def get_work_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["education"] = update.message.text
    await send_html_message(update=update, context=context, text="Describe your <b>work experience</b>:")

    return WORK_EXPERIENCE


async def get_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["work_experience"] = update.message.text
    await send_html_message(update=update, context=context, text="List your <b>skills</b>:")

    return SKILLS


async def get_additional_information(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["skills"] = update.message.text
    await send_html_message(
        update=update,
        context=context,
        text="<b>Additional information</b> (Certifications, Languages, Hobby...) or write \'<b>no</b>\' to skip:"
    )
    return ADDITIONAL_INFORMATION


async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.message.text.strip()

    if ":" in message:
        category, value = message.split(":", 1)
        category = category.strip().lower()
        value = value.strip()
        context.user_data[category] = value
    else:
        context.user_data["additional_information"] = update.message.text

    context.user_data.pop("summary", None)

    fields = ["position", "name", "contacts", "education", "work_experience", "skills", "additional_information"]
    summary = "\n".join(
        f"'{field}:' {context.user_data.get(field, '—')}" for field in fields
    )
    context.user_data["summary"] = summary

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Check the entered data:\n{summary}\n\nConfirm or select Edit",
        reply_markup=get_resume_button()
    )
    return CONFIRM


async def finalize_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await send_html_message(
        update=update,
        context=context,
        text="Please copy one 'category:' (e.g., <b>skills:</b> ) and enter corrected data."
    )
    return ADDITIONAL_INFORMATION


async def generate_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["mode"] = None
    query = update.callback_query
    await query.answer()

    # Connecting the assistant and DB
    openai_client: OpenAIClient = context.bot_data["openai_client"]
    assistant_id = config.ai_assistant_resume_mileshkin_id
    thread_repository: GptThreadRepository = context.bot_data["thread_repository"]

    tg_user_id = update.effective_user.id
    mode = SessionMode.RESUME.value

    thread_id = await thread_repository.get_thread_id(tg_user_id, mode)

    if thread_id is None:
        thread = await openai_client.create_thread()
        thread_id = thread.id
        await thread_repository.create_thread(tg_user_id, mode, thread_id)


    edit_user_data = context.user_data

    user_message = f"Use this information to write a user summary.\n{edit_user_data}"

    # Saving users message in DB
    await thread_repository.add_message(thread_id, role=MessageRole.USER.value, content=user_message)

    # Get resume from assistant
    try:
        reply = await openai_client.ask(
            assistant_id=assistant_id,
            thread_id=thread_id,
            user_message=user_message
        )
    except OpenAIError as e:
        logger.warning(f"Assistant failed to respond in /resume, generate_resume(): {e}")
        await update.message.reply_text("Assistant failed to respond. Please try again later.")
        return FORMAT_FILE

    reply = sanitize_html(reply)
    context.user_data["resume"] = reply

    # Saving assistants message in DB
    await thread_repository.add_message(thread_id, role=MessageRole.ASSISTANT.value, content=reply)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Your resume is ready.\n\nIn what format would you like to download it?",
        reply_markup=get_resume_format_file_button()
    )
    return FORMAT_FILE


async def convert_text_to_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    format_file = query.data
    resume = context.user_data.get("resume", "")

    try:
        resume_file = await convert_to_file(resume, format_file.lower())
    except ValueError as e:
        logger.warning(f"Invalid format selected convert_text_to_file(): {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Unsupported format. Please choose PDF or DOCX."
        )
        return FORMAT_FILE
    except Exception as e:
        logger.exception(f"Unexpected error during conversion convert_text_to_file(): {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Something went wrong during file conversion. Please try again later."
        )
        return ConversationHandler.END

    file_name = f"resume.{format_file}"

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=resume_file,
        filename=file_name,
        caption=f"Here is your resume as {format_file}."
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"If necessary, select another format:",
        reply_markup=get_resume_format_file_button_end()
    )
    return FORMAT_FILE


async def end_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    return await start(update, context)


resume_handler = ConversationHandler(
    entry_points=[CommandHandler("resume", get_position)],
    states={
        POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contacts)],
        CONTACTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_education)],
        EDUCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_work_experience)],
        WORK_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_skills)],
        SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_additional_information)],
        ADDITIONAL_INFORMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_data)],
        CONFIRM: [
            CallbackQueryHandler(generate_resume, pattern="^confirm$"),
            CallbackQueryHandler(finalize_resume, pattern="^edit$")
        ],
        FORMAT_FILE: [
            CallbackQueryHandler(convert_text_to_file, pattern="^PDF$"),
            CallbackQueryHandler(convert_text_to_file, pattern="^DOCX$"),
            CallbackQueryHandler(start, pattern="^complete$")
        ]
    },
    fallbacks=[]
)


