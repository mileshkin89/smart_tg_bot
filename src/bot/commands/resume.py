from telegram import Update
from telegram.error import BadRequest
from bot.message_sender import send_html_message, send_image_bytes
from bot.resource_loader import load_message, load_image, load_prompt
from services import OpenAIClient
from .start import start
from bot.keyboards import get_resume_button, get_resume_format_file_button, get_resume_format_file_button_end
from bot.sanitize_html import sanitize_html
from bot.file_converter import convert_to_file

from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)


POSITION = "POSITION"
NAME = "NAME"
CONTACTS = "CONTACTS"
EDUCATION = "EDUCATION"
WORK_EXPERIENCE = "WORK EXPERIENCE"
SKILLS = "SKILLS"
ADDITIONAL_INFORMATION = "ADDITIONAL INFORMATION"
CONFIRM = "CONFIRM"
FORMAT_FILE = "FORMAT FILE"


async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE):

    intro = await load_message("resume")
    image_bytes = await load_image("resume")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=f"{intro}")
    await send_html_message(update=update, context=context, text=f"\n\nWrite what position you are applying for:")

    return POSITION


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["position"] = update.message.text
    await send_html_message(update=update, context=context, text="Enter your full name:")

    return NAME


async def get_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["name"] = update.message.text
    await send_html_message(update=update, context=context, text="Enter your contact information (phone, email):")

    return CONTACTS


async def get_education(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["contacts"] = update.message.text
    await send_html_message(update=update, context=context, text="Describe your education:")

    return EDUCATION


async def get_work_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["education"] = update.message.text
    await send_html_message(update=update, context=context, text="Describe your work experience:")

    return WORK_EXPERIENCE


async def get_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["work_experience"] = update.message.text
    await send_html_message(update=update, context=context, text="List your skills:")

    return SKILLS


async def get_additional_information(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["skills"] = update.message.text
    await send_html_message(
        update=update,
        context=context,
        text="Additional information (Certifications, Languages, Hobby...) or write \'no\' to skip:"
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
        text="Please copy one 'category:' (e.g., skills:) and enter corrected data."
    )

    return ADDITIONAL_INFORMATION


async def generate_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    edit_user_data = context.user_data
    user_message = f"Use this information to write a user summary.\n{edit_user_data}"
    system_prompt = await load_prompt("resume")

    openai_client: OpenAIClient = context.bot_data["openai_client"]

    reply = await openai_client.ask(user_message=user_message, system_prompt=system_prompt)
    reply = sanitize_html(reply)
    context.user_data["resume"] = reply

    try:
        await send_html_message(update=update, context=context, text=f"Here is your resume draft:\n\n{reply}")
    except BadRequest as e:
        print(f"Error sending HTML message: {e}")

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
    print(format_file)
    resume = context.user_data.get("resume", "")

    resume_file = await convert_to_file(resume, format_file.lower())

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


