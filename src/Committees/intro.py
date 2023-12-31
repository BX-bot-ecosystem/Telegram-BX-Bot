import time
from telegram import Update
from telegram.ext import (
    ContextTypes,
)
from .config import telegram_list

INITIAL, LORE, CONTINUE, COMMITTEES = range(4)

async def intro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Tell them about the different committees"""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    time.sleep(1.2)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Committees are the central part of our piratey student life, there is lots of them and if you don't find the one you want, you can even create a new one")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    time.sleep(0.9)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Here is the full list of committees:\n -  " + telegram_list)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    time.sleep(1.1)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="To enter a committee section just press the command next to its name")
    time.sleep(1.1)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Once you are in remember to use /help to find out what you can do and /exit once you are ready to leave")
    return INITIAL
