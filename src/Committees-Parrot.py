import logging
import json
import random
import string
from uuid import uuid4
import telegram.error

from utils import db, config, passwords

with open('../credentials.json') as f:
    tokens = json.load(f)
    committees_token = tokens["SailoreCommitteesBot"]
    parrot_token = tokens["SailoreParrotBot"]
    sailore_token = tokens["SailoreBXBot"]

with open('../data/Committees/committees.json') as f:
    committees = json.load(f)

from telegram import __version__ as TG_VER
try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class Committees_hub:
    def __init__(self):
        self.list = list(committees.keys())
        self.list.insert(0, '')
        self.committees_list = "\n -  ".join(self.list)
        self.active_committee = ''
        self.HOME, self.LOGIN, self.VERIFICATION, self.HUB, self.MESSAGE, self.ACCESS, self.RIGHTS, self.APPLY_ROLE, self.CONFIRMATION = range(9)
        self.access_list = []
        self.admins_rights = {}
        self.admin_to_change = ''
        self.role_to_apply = ''
        self.admins_ids = {}
        self.committees_handler=ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT, self.start)],
            states={
                self.HOME: [
                    MessageHandler(filters.TEXT, self.start)
                ],
                self.LOGIN: [
                    CommandHandler("password", self.password_access),
                    MessageHandler(filters.TEXT, self.login)
                ],
                self.VERIFICATION: [
                    MessageHandler(filters.TEXT, self.verify_password)
                ],
                self.HUB: [
                    CommandHandler("subs", self.give_subs),
                    CommandHandler("message", self.message),
                    CommandHandler("event", self.event),
                    CommandHandler("access", self.access),
                    CommandHandler("logout", self.logout),
                    MessageHandler(filters.TEXT, self.hub)
                ],
                self.MESSAGE: [MessageHandler(filters.TEXT, self.parrot)],
                self.ACCESS: [
                    CommandHandler("password", self.password),
                    CommandHandler("rights", self.rights)
                ],
                self.RIGHTS: [
                    CallbackQueryHandler(self.chose_role)
                ],
                self.APPLY_ROLE: [
                    CallbackQueryHandler(self.apply_role)
                ],
                self.CONFIRMATION: [
                    CallbackQueryHandler(self.confirmation)
                ]
            },
            fallbacks=[MessageHandler(filters.TEXT, self.start)]
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        info = db.get_user_info(update.effective_user)
        rights = info["rights"]
        access_list = db.db_to_list(rights)
        message_list = db.list_to_telegram(access_list)
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="This bot is for committees to manage their bot sections")
        if len(access_list) == 0:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="Right now you don't have access to any committees")
        else:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="Right now you have access to the following committees \n" + message_list)
            self.access_list = access_list
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="To gain admin access to a new committee ask your committee head for a one time password")
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Once generated use the command /password to gain access")
        return self.LOGIN
    async def login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        committee = update.message.text
        if committee in self.access_list:
            self.active_committee = committees[committee]
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text=f"You have successfully logged into {self.active_committee}")
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="From here you can check your /subs, send them a /message, upload an /event to the google calendar or manage the /access to this committee hub")
            return self.HUB
        else:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="That is not a valid choice, either you don't have access or it doesn't exist")
            return self.HOME

    async def password_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="What is your one time password?")
        return self.VERIFICATION

    async def verify_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text
        committee_name = password.split(':')[0]
        committee_command = [key for key in committees.keys() if committees[key] == committee_name][0]
        if not db.use_one_time_pass(password, committee_name):
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Error: either you entered an incorrect password or one has not been generated")
        result = db.add_access_rights(update.effective_user, committee_name, committee_command)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Your rights have been successfully updated")

        return self.HOME

    async def hub(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text=f"You are logged into {self.active_committee}")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="From here you can check your /subs, send them a /message, upload an /event to the google calendar or manage the /access to this committee hub")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="If you want to access other committee, then /logout")
        return self.HUB
    """
    async def password_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        committee = update.message.text
        if committee in committees.keys():
            self.active_committee = committees[committee]
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="What is the password?",)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="For security reasons you must type it as an inline query (@SailoreCommitteesBot <password>) selecting the password mode", )
            return self.PASS_INPUT
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="That is not a valid committee")
            return self.LOGIN

    async def password_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = self.password
        self.password = ''
        print(password)
        if passwords.verify_password(db.get_pass_committee(self.active_committee),password):
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Logged in successfully")
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="From here you can check your /subscriptors, send then a /message, manage your /settings or upload an /event to the google calendar")
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Remember to /logout after you finish using so that no one can access your committee hub")
            db.record_logging(update.effective_user, self.active_committee)
            return self.COMMITTEE
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Incorrect password")
            db.user_wrong_password(update.effective_user)
            return self.ADMIN

    async def new_password_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass
    """
    async def give_subs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keys = db.subs_of_committee(self.active_committee)
        users_info = db.get_users_info(keys)
        names = [user["fullname"] for user in users_info]

        names.insert(0, '')
        name_list = '\n - '.join(names)
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text=f"Your committee has a total of {len(names) - 1} subs")
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="This is the full list:" + name_list)
        return self.HUB
    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="What message do you wish to send to your subscriptors?")
        return self.MESSAGE
    async def parrot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message.text
        keys = db.subs_of_committee(self.active_committee)
        users_info = db.get_users_info(keys)
        parrot_bot = Bot(parrot_token)
        sailore_bot = Bot(sailore_token)
        counter = 0
        for user in users_info:
            try:
                await parrot_bot.send_message(chat_id=user['id'],
                                               text=f'Hello {user["name"]}, this is a communication from {self.active_committee}:')
                await parrot_bot.send_message(chat_id=user['id'], text=message)
            except telegram.error.BadRequest:
                counter += 1
                await sailore_bot.send_message(chat_id=user['id'],
                    text=f"""Hello {user['name']}, a communication from one of your subscriptions was just sent to you but you didn't receive it as you haven't signed in into t.me/SailoreParrotBot""")
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Successfully echoed your message")
        if counter > 0:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text=f"We also notified {counter} of your users which didn't sign into @SailoreParrotBot")
        return self.HUB

    async def event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Functionality to be implemented")

    async def access(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        access_granted = db.get_committee_access(self.active_committee)
        roles = ["Prez: All functionalities + access management", "Admin: All functionalities", "Comms: Message functionality", "Events: Events functionality"]
        keys = ['user:' + user_id for user_id in access_granted.keys()]
        admins_info = db.get_users_info(keys)

        self.admins_rights = {admin['name']: access_granted[admin['id']] for admin in admins_info}
        self.admins_ids = {admin['name']: admin['id'] for admin in admins_info}
        current_admins = [f"{admin['name']}: {access_granted[admin['id']]}" for admin in admins_info]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Inside any committee hub the following roles are allowed: \n" + '\n'.join(roles))
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="The current users with access are: \n" + '\n'.join(current_admins))
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Do you want to generate a one-time /password to register a new user or change the current /rights")
        return self.ACCESS
    async def password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        new_password=self.active_committee + ':' + ''.join(random.choices(string.digits + string.ascii_letters, k=10))
        db.add_one_time_pass(new_password, self.active_committee)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"The password generated is <b>{new_password}</b>, the default rights are admin for new users",
                                       parse_mode=ParseMode.HTML)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"This password only has one use, send it to the person you want to give access")
        return self.HUB
    async def rights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[InlineKeyboardButton(admin, callback_data=admin)] for admin in self.admins_rights.keys()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Who's right do you want to change?",
                                       reply_markup=reply_markup)
        return self.RIGHTS

    async def chose_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        await query.answer()
        self.admin_to_change = query.data
        roles = ['Prez', 'Admin', 'Comms', 'Events', 'None']
        keyboard = [[InlineKeyboardButton(role, callback_data=role)] for role in roles]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"Which role do you want to assign to {query.data}",
                                      reply_markup=reply_markup)
        return self.APPLY_ROLE

    async def apply_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        self.role_to_apply = query.data
        keyboard = [[InlineKeyboardButton('yay', callback_data='True'), InlineKeyboardButton('nay', callback_data='False')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if self.role_to_apply == 'Prez':
            await query.edit_message_text(text=f"This will make {self.admin_to_change} Prez and it will remove your rights, are you sure?",
                                          reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=f"This will make {self.admin_to_change} {self.role_to_apply}, are you sure?",
                                          reply_markup=reply_markup)
        return self.CONFIRMATION

    async def confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if not bool(query.data):
            await query.edit_message_text(text="Change of rights cancelled")
            return self.HUB
        if self.role_to_apply == 'Prez':
            self.admins_rights[update.effective_user.name] = 'Admin'
        if self.role_to_apply == 'None':
            del self.admins_rights[self.admin_to_change]
            committee_command = [key for key in committees.keys() if committees[key] == self.active_committee][0]
            db.eliminate_access_rights(self.admins_ids[self.admin_to_change], self.active_committee, committee_command)
            await query.edit_message_text(text=f"{self.admin_to_change} has been removed access to this committee hub")
            return self.HUB
        self.admins_rights[self.admin_to_change] = self.role_to_apply
        new_rights = {self.admins_ids[admin]: self.admins_rights[admin] for admin in self.admins_rights.keys()}
        db.change_committee_access(self.active_committee, new_rights)
        await query.edit_message_text(text=f"{self.admin_to_change} has been applied the role of {self.role_to_apply}")
        return self.HUB

    """
    async def password_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Please retype your old password for security reasons")
        return self.PASSWORD_CHANGE

    async def password_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text
        if passwords.verify_password(db.get_pass_committee(self.active_committee), password):
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Type the new password")
            return self.NEW_PASSWORD
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Incorrect")
            return self.SETTINGS

    async def new_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.new_pass = update.message.text
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Type the new password")
    """
    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Successful logout")
        return self.HOME

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(committees_token).build()
    committees_hub = Committees_hub()
    application.add_handler(committees_hub.committees_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()