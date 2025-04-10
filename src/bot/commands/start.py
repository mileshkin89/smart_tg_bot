from telegram import Update
from telegram.ext import ContextTypes
from bot.message_sender import send_html_message, send_image_bytes, show_menu
from bot.resource_loader import load_message, load_image, load_menu


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command and displays the main menu.

    Loads and sends the main welcome message, image, and keyboard with available bot commands.
    Also resets the user's current session mode.

    Args:
        update (telegram.Update): The incoming update from the Telegram user.
        context (telegram.ext.ContextTypes.DEFAULT_TYPE): Context object containing bot and user data.

    Side Effects:
        - Sends a welcome image and message.
        - Displays a button-based menu to the user.
        - Resets context.user_data["mode"] to None.
    """
    text = await load_message("main")
    image_bytes = await load_image("main")
    menu_commands = await load_menu("main")

    await send_image_bytes(update=update, context=context, image_bytes=image_bytes)
    await send_html_message(update=update, context=context, text=text)
    await show_menu(update=update, context=context, commands=menu_commands)