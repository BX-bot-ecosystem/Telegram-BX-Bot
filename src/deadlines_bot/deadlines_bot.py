import json
import random
import string
import telegram.error
import enum

from telegram_bot_calendar import WYearTelegramCalendar, LSTEP
from utils import db, gc
import utils

utils.Vcheck.telegram()
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CallbackContext
)

from dotenv import load_dotenv
import os
load_dotenv()

DEADLINE_TOKEN = os.getenv("DEADLINE_BOT")
DEADLINE_MANAGER_TOKEN = os.getenv("DEADLINE_MANAGER")

utils.logger(__name__)

class Activity(enum.Enum):
    HOME = 1
    LOGIN = 2
    VERIFICATION = 3
    HUB = 4
    MESSAGE = 5
    ACCESS = 6
    RIGHTS = 7
    DEADLINE = 8
    DATE = 9
    START_TIME = 10
    END_TIME = 11
    NAME = 12
    SUMMARY = 13
    CONFIRMATION_DEADLINE = 14
    MODIFY_DEADLINE = 15
class Right_changer:
    class State(enum.Enum):
        USER = 1
        ROLE = 2
        CONFIRMATION = 3
        MORE = 4
    def __init__(self, user_rights):
        self.user_rights = user_rights
        self.active_user = [user for user in user_rights.keys() if user_rights[user] == 'Prez'][0]
        self.keyboard = InlineKeyboardMarkup([[]])
        self.state = self.State.USER
        self.new_user_rights = user_rights
        self.params = {}

    def build(self):
        if self.state == self.State.USER:
            self._build_users()
        if self.state == self.State.ROLE:
            self._build_role()
        if self.state == self.State.CONFIRMATION:
            self._build_confirmation()
        if self.state == self.State.MORE:
            self._build_more()

    def process(self, call_data):
        # callback = user_role_confirmation_more
        params = call_data.split('_')
        params = dict(zip(['user', 'role', 'confirmation', 'more'][:len(params)], params))
        self.params = params
        if len(params) == 1:
            self.state = self.State.ROLE
            return False, 'role', None
        elif len(params) == 2:
            self.state = self.State.CONFIRMATION
            return False, 'confirm', None
        elif len(params) == 3:
            if params['confirmation'] == 'yay':
                self.new_user_rights[self.params['user']] = self.params['role']
                if self.params['role'] == 'Prez':
                    self.new_user_rights[self.active_user] = 'Admin'
                self.state = self.State.MORE
                return True, 'more', self.new_user_rights
            self.state = self.State.MORE
            return False, 'more', None
        elif len(params) == 4:
            if params['more'] == 'yay':
                self.user_rights = self.new_user_rights
                self.state = self.State.USER
                return True, 'user', None
            return False, 'user', None

    def _build_users(self):
        user_list = [[user] for user in self.user_rights.keys() if user != self.active_user]
        self.keyboard = self._build_keyboard(user_list)

    def _build_role(self):
        roles = [['Admin'], ['None']]
        self.keyboard = self._build_keyboard(roles)

    def _build_confirmation(self):
        confirmation = [['yay', 'nay']]
        self.keyboard = self._build_keyboard(confirmation)

    def _build_more(self):
        more = [['yay', 'nay']]
        self.keyboard = self._build_keyboard(more)

    def _build_keyboard(self, elements):
        keyboard = []
        for i, row in enumerate(elements):
            keyboard.append([])
            for element in row:
                callback = self._build_callback(element)
                keyboard[i].append(InlineKeyboardButton(element, callback_data=callback))
        return InlineKeyboardMarkup(keyboard)

    def _build_callback(self, element):
        if self.state == self.State.USER:
            return element
        if self.state == self.State.ROLE:
            return f'{self.params["user"]}_{element}'
        if self.state == self.State.CONFIRMATION:
            return f'{self.params["user"]}_{self.params["role"]}_{element}'
        if self.state == self.State.MORE:
            return f'{self.params["user"]}_{self.params["role"]}_{self.params["confirmation"]}_{element}'

class time_picker:
    class State(enum.Enum):
        HOUR = 1
        MINUTES = 2
    def __init__(self):
        self.hour = None
        self.keyboard = InlineKeyboardMarkup([[]])
        self.state = self.State.HOUR

    def build(self):
        if self.state == self.State.HOUR:
            self.create_hours_keyboard()
        if self.state == self.State.MINUTES:
            self.create_minutes_keyboard()

    def process(self, data):
        if self.hour is None:
            self.hour = data
            self.state = self.State.MINUTES
            return False, None
        else:
            self.hour = None
            self.state = self.State.HOUR
            return True, data


    def create_minutes_keyboard(self):
        keyboard = [[]]
        hour = self.hour
        times = [hour + ':00', hour + ':15', hour + ':30', hour + ':45']
        for time in times:
            keyboard[0].append(InlineKeyboardButton(time, callback_data=time))
        self.keyboard = InlineKeyboardMarkup(keyboard)

    def create_hours_keyboard(self):
        keyboard = []
        hours = [str(i).zfill(2) for i in range(0, 24)]

        for i in range(0, 24, 6):
            row = []
            for j in range(6):
                hour = hours[i + j]
                row.append(InlineKeyboardButton(hour, callback_data=hour))
            keyboard.append(row)
        self.keyboard = InlineKeyboardMarkup(keyboard)

class deadline_changer:
    class State(enum.Enum):
        DEADLINE = 1
        PROPERTY = 2
        VALUE = 3
        MORE = 4
        OTHER_DEADLINE = 5
    def __init__(self, deadlines):
        self.deadlines = deadlines
        self.deadline = None
        self.params = {}
        self.property = None
        self.state = self.State.OTHER_DEADLINE

    def build(self):
        if self.state == self.State.DEADLINE:
            self._build_deadlines()
        elif self.state == self.State.PROPERTY:
            self._build_properties()
        elif self.state == self.State.MORE:
            self._build_more()
        elif self.state == self.State.OTHER_DEADLINE:
            self._build_other_deadline()

    def process(self, call_data):
        if self.state == self.State.OTHER_DEADLINE:
            if call_data == 'yay':
                self.state = self.State.DEADLINE
                return True, 'deadline', None
            return False, 'deadline', None
        if self.state == self.State.DEADLINE:
            self.state = self.State.PROPERTY
            self.deadline = [deadline for deadline in self.deadlines if deadline["summary"] == call_data][0]
            return True, 'property', None
        if self.state == self.State.PROPERTY:
            if call_data == 'Delete Deadline':
                self.state = self.State.OTHER_DEADLINE
                return False, 'delete', self.deadline
            self.state = self.State.VALUE
            self.property = call_data
            return True, 'value', None
        if self.state == self.State.VALUE:
            self.state = self.State.MORE
            self.change(self.property, call_data)
            return True, 'more', None
        if self.state == self.State.MORE:
            if call_data == 'yay':
                self.state = self.State.PROPERTY
                return True, 'property', None
            self.state = self.State.OTHER_DEADLINE
            self.check_dates()
            return False, 'other', self.deadline

    def _build_deadlines(self):
        deadline_names = [[deadline_data['summary']] for deadline_data in self.deadlines]
        self.keyboard = self._build_keyboard(deadline_names)

    def _build_properties(self):
        properties = [['Date'], ['Start'], ['End'], ['Name'], ['Description'], ['Delete Deadline']]
        self.keyboard = self._build_keyboard(properties)

    def _build_more(self):
        more = [['yay', 'nay']]
        self.keyboard = self._build_keyboard(more)

    def _build_other_deadline(self):
        other = [['yay', 'nay']]
        self.keyboard = self._build_keyboard(other)

    def _build_keyboard(self, elements):
        keyboard = []
        for i, row in enumerate(elements):
            keyboard.append([])
            for element in row:
                keyboard[i].append(InlineKeyboardButton(element, callback_data=element))
        return InlineKeyboardMarkup(keyboard)

    def change(self, property_changed, data):
        if property_changed == 'Name':
            self.deadline["summary"] = data
        if property_changed == 'Description':
            self.deadline["description"] = data
        if property_changed == 'Date':
            self.deadline["start"]["dateTime"] = gc.changeDate(self.deadline["start"]["dateTime"], data)
            self.deadline["end"]["dateTime"] = gc.changeDate(self.deadline["end"]["dateTime"], data)
        if property_changed == 'Start':
            self.deadline["start"]["dateTime"] = gc.changeTime(self.deadline["start"]["dateTime"], data, False)
        if property_changed == 'End':
            self.deadline["end"]["dateTime"] = gc.changeTime(self.deadline["end"]["dateTime"], data, False)

    def check_dates(self):
        if self.deadline["end"]["dateTime"]  < self.deadline["start"]["dateTime"]:
            self.deadline["end"]["dateTime"] = gc.nextDay(self.deadline["end"]["dateTime"])

class Deadline_handler:
    def __init__(self, active_major):
        self.state = Activity.DEADLINE
        self.active_major = active_major
        self.date = ''
        self.start_time = ''
        self.end_time = ''
        self.name = ''
        self.user_rights = ''
        self.description = ''
        self.getting_data = False
        self.time_picker = time_picker()
        self.deadline_changer = None
        self.deadline_handler = ConversationHandler(
            entry_points=[CommandHandler("deadline", self.deadlines)],
            states={
                self.state.DEADLINE: [CommandHandler("view", self.view), CommandHandler("create", self.create)],
                self.state.DATE: [CallbackQueryHandler(self.date_selection)],
                self.state.START_TIME: [CallbackQueryHandler(self.select_start)],
                self.state.END_TIME: [CallbackQueryHandler(self.select_end)],
                self.state.NAME: [MessageHandler(filters.TEXT, self.naming)],
                self.state.SUMMARY: [MessageHandler(filters.TEXT, self.summary)],
                self.state.CONFIRMATION_DEADLINE: [CallbackQueryHandler(self.confirmation)],
                self.state.MODIFY_DEADLINE: [CallbackQueryHandler(self.modify_deadline), MessageHandler(filters.TEXT, self.modify_deadline)]
            },
            fallbacks=[MessageHandler(filters.TEXT, self.back)],
            map_to_parent={
                self.state.HUB: self.state.HUB,
            }
        )
    async def back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="You are back to the hub")
        return self.state.HUB

    async def deadlines(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.user_rights == 'Comms':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="You don't have access rights for this functionality")
            return self.state.HUB
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Do you want to /create a new deadline or to /view the already added deadlines")
        return self.state.DEADLINE

    async def view(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        deadlines = gc.get_major_deadlines(self.active_major)
        deadline_descriptions = []
        for item in deadlines:
            deadline_descriptions.append(gc.deadline_presentation_from_api(item))
        message = '\n -------------------------------------- \n'.join(deadline_descriptions)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="The deadlines already planned by your major are:")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message,
                                       parse_mode=ParseMode.HTML)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Do you want to change any of these deadlines?",
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('yay', callback_data='yay')], [InlineKeyboardButton('nay', callback_data='nay')]]))
        self.deadline_changer = deadline_changer(deadlines)
        return self.state.MODIFY_DEADLINE

    async def modify_deadline(self, update: Update, context: CallbackContext):
        if self.deadline_changer.property in ['Name', 'Description'] and self.getting_data:
            data = update.message.text
            self.getting_data = False
        else:
            query = update.callback_query
            await query.answer()
            data = query.data
        if self.deadline_changer.property == 'Date' and self.getting_data:
            ##Handles the date selection
            result, key, step = WYearTelegramCalendar().process(data)
            if not result and key:
                await query.edit_message_text(f"Enter the new date", reply_markup=key)
                context.user_data["step"] = step  # Update the step in user_data
                return self.state.MODIFY_DEADLINE
            elif result:
                await query.edit_message_text(text=f'Selected {data}')
                data = result
                self.getting_data = False

        if self.deadline_changer.property == 'Start' and self.getting_data:
            key, result = self.time_picker.process(data)
            self.time_picker.build()
            if result is None:
                await query.edit_message_text(text='Enter the new starting time',
                                              reply_markup=self.time_picker.keyboard)
                return self.state.MODIFY_DEADLINE
            else:
                await query.edit_message_text(text=f'Selected {data}')
                data = result
                self.getting_data = False

        if self.deadline_changer.property == 'End' and self.getting_data:
            key, result = self.time_picker.process(data)
            self.time_picker.build()
            if result is None:
                await query.edit_message_text(text='Enter the new ending time',
                                              reply_markup=self.time_picker.keyboard)
                return self.state.MODIFY_DEADLINE
            else:
                data = result
                await query.edit_message_text(text=f'Selected {data}')
                self.getting_data = False



        key, state, deadline = self.deadline_changer.process(data)
        if not key and state == 'delete':
            gc.deleteDeadline(deadline)
            await query.edit_message_text(text="Alright")
            return self.state.HUB
        if not key and state == 'deadline':
            await query.edit_message_text(text="Alright")
            return self.state.HUB
        message = {'deadline': 'Which deadline do you want to modify?', 'property': 'Which property do you want to change?',
                   'more': 'Do you want to change other properties', 'other': 'Changes saved\nDo you want to change another deadline?'}
        if key and state == 'more':
            self.deadline_changer.build()
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=message[state], reply_markup=self.deadline_changer.keyboard)
            return self.state.MODIFY_DEADLINE

        if not key and state == 'other':
            self.deadline_changer.build()
            gc.update_deadline(deadline)
            await query.edit_message_text(text=message[state], reply_markup=self.deadline_changer.keyboard)
            return self.state.MODIFY_DEADLINE

        if key and state != 'value':
            self.deadline_changer.build()
            await query.edit_message_text(text=message[state], reply_markup=self.deadline_changer.keyboard)
            return self.state.MODIFY_DEADLINE
        property_to_change = self.deadline_changer.property
        self.getting_data = True
        if property_to_change in ['Name', 'Description']:
            await query.edit_message_text(text=f"Enter the new {property_to_change.lower()}")
            return self.state.MODIFY_DEADLINE
        if property_to_change == 'Date':
            calendar, step = WYearTelegramCalendar().build()
            await query.edit_message_text(text=f"Enter the new date", reply_markup=calendar)
            return self.state.MODIFY_DEADLINE
        if property_to_change == 'Start':
            self.time_picker.build()
            await query.edit_message_text(text="Enter the new starting time",
                                          reply_markup=self.time_picker.keyboard)
            return self.state.MODIFY_DEADLINE
        if property_to_change == 'End':
            self.time_picker.build()
            await query.edit_message_text(text="Enter the new ending time",
                                          reply_markup=self.time_picker.keyboard)
            return self.state.MODIFY_DEADLINE



    async def create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        calendar, step = WYearTelegramCalendar().build()

        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="When do you want to create an deadline?",
                                       reply_markup=calendar)
        return self.state.DATE

    async def date_selection(self, update: Update, context: CallbackContext):
        query = update.callback_query
        data = query.data

        result, key, step = WYearTelegramCalendar().process(data)

        if not result and key:
            await query.edit_message_text(f"Select {LSTEP[step]}", reply_markup=key)
            context.user_data["step"] = step  # Update the step in user_data
            return self.state.DATE
        elif result:
            await query.edit_message_text(f"You selected the date {result}")
            self.date = result
            self.time_picker.build()

            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="At what time does your deadline start?",
                                           reply_markup=self.time_picker.keyboard)
            return self.state.START_TIME

    async def select_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        key, result = self.time_picker.process(query.data)
        self.time_picker.build()
        if result is None:
            await query.edit_message_text(text='At what time does your deadline start?',
                                          reply_markup=self.time_picker.keyboard)
            return self.state.START_TIME
        self.start_time = result
        await query.edit_message_text(text=f'Selected {self.start_time}')
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="When does it end?",
                                       reply_markup=self.time_picker.keyboard)
        return self.state.END_TIME

    async def select_end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        key, result = self.time_picker.process(query.data)
        self.time_picker.build()
        if result is None:
            await query.edit_message_text(text='When does it end?',
                                          reply_markup=self.time_picker.keyboard)
            return self.state.END_TIME
        self.end_time = result
        await query.edit_message_text(text=f'Selected {self.end_time}')
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Give it a name")
        return self.state.NAME

    async def naming(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.name = update.message.text
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Give a brief description of your deadline")
        return self.state.SUMMARY

    async def summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.description = update.message.text
        deadline_description = gc.deadline_presentation_from_data(self.active_major, self.date, self.name, self.start_time, self.end_time, self.description)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Current Deadline:\n {deadline_description}",
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('yay', callback_data='True'), InlineKeyboardButton('nay', callback_data='False')]]),
                                       parse_mode=ParseMode.HTML)
        return self.state.CONFIRMATION_DEADLINE

    async def confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == 'False':
            await query.edit_message_text(text="Deadline upload cancelled")
            return self.state.HUB
        await query.edit_message_text(text=f"The deadline has been uploaded to the google calendar, users will be able to see it on your major part of SailoreBXBot two weeks prior to the deadline")
        gc.create_deadline(self.date, self.start_time, self.end_time, self.active_major, self.name, self.description)
        return self.state.HUB


class Access_handler:
    def __init__(self, active_major):
        self.active_major = active_major
        access_granted = db.get_major_access(self.active_major)
        keys = ['user:' + user_id for user_id in access_granted.keys()]
        admins_info = db.get_users_info(keys)
        self.admins_rights = {admin['name']: access_granted[admin['id']] for admin in admins_info}
        self.admins_ids = {admin['name']: admin['id'] for admin in admins_info}
        self.state = Activity.ACCESS
        self.access_list = []
        self.user_rights = None
        self.right_changer = Right_changer(self.admins_rights)
        self.access_handler=ConversationHandler(
            entry_points=[CommandHandler("access", self.access)],
            states={
                self.state.ACCESS: [
                    CommandHandler("password", self.password),
                    CommandHandler("rights", self.rights),
                    CommandHandler("back", self.back)
                ],
                self.state.RIGHTS: [
                    CallbackQueryHandler(self.chose_role)
                ],
            },
            fallbacks=[MessageHandler(filters.TEXT, self.access)],
            map_to_parent={
                self.state.HUB: self.state.HUB
            }
        )

    async def back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="You are back to the hub")
        return self.state.HUB
    async def access(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.user_rights == 'Prez':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="You don't have access rights for this functionality")
            return self.state.HUB
        roles = ["Prez: All functionalities + access management", "Admin: All functionalities", "Comms: Message functionality", "Events: Events functionality"]
        current_admins = [f"{key}: {value}" for key, value in self.admins_rights.items()]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Inside any major hub the following roles are allowed: \n" + '\n'.join(roles))
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="The current users with access are: \n" + '\n'.join(current_admins))
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Do you want to generate a one-time /password to register a new user or change the current /rights (you can also go /back to the hub)")
        return self.state.ACCESS
    async def password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        new_password=self.active_major + ':' + ''.join(random.choices(string.digits + string.ascii_letters, k=10))
        db.add_one_time_pass(new_password, self.active_major)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"The password generated is <b>{new_password}</b>, the default rights are admin for new users",
                                       parse_mode=ParseMode.HTML)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"This password only has one use, send it to the person you want to give access")
        return self.state.HUB
    async def rights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.right_changer = Right_changer(self.admins_rights)
        self.right_changer.build()
        keyboard = self.right_changer.keyboard
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Who's right do you want to change?",
                                       reply_markup=keyboard)
        return self.state.RIGHTS
    async def chose_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        await query.answer()
        data = query.data
        result, state, rights = self.right_changer.process(data)
        if result and state=='more':
            #save the changes
            self.admins_rights = self.right_changer.new_user_rights
        if not result and state=='user':
            if 'None' in self.admins_rights.values():
                users_to_eliminate = [user for user in self.admins_rights.keys() if self.admins_rights[user] == 'None']
                for user in users_to_eliminate:
                    del self.admins_rights[user]
                    major_command = majors[self.active_major]["command"]
                    db.eliminate_access_rights(self.admins_ids[user], self.active_major, major_command)
            new_rights = {self.admins_ids[admin]: self.admins_rights[admin] for admin in self.admins_rights.keys()}
            db.change_major_access(self.active_major, new_rights)
            await query.edit_message_text(text="The rights have been updated accordingly")
            return self.state.HUB
        self.right_changer.build()
        keyboard = self.right_changer.keyboard
        params = data.split('_')
        message = {'user': "Who's right do you want to change?", 'role': "Which role do you want to apply? \n (Selecting Prez will change your role to Admin)", 'confirm': f"Confirm the change of {params[0]} to {params[-1]}", 'more': "Do you want to make any other changes"}
        await query.edit_message_text(text=message[state], reply_markup=keyboard)
        return self.state.RIGHTS

class Majors_Login:
    def __init__(self):
        self.active_major = ''
        self.state = Activity.HOME
        self.major_hub = ''
        self.access_list = []
        self.login_handler=ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT, self.start)],
            states={
                self.state.HOME: [
                    MessageHandler(filters.TEXT, self.start)
                ],
                self.state.LOGIN: [
                    CommandHandler("password", self.password_access),
                    MessageHandler(filters.TEXT, self.login)
                ],
                self.state.VERIFICATION: [
                    MessageHandler(filters.TEXT, self.verify_password)
                ],
                self.state.HUB: [

                ]
            },
            fallbacks=[MessageHandler(filters.TEXT, self.start)]
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        info = db.get_user_info(update.effective_user)
        rights = info["deadlines"]
        access_list = db.db_to_list(rights)
        message_list = db.list_to_telegram(access_list)
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="This bot is for student reps to manage their deadlines")
        if len(access_list) == 0:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="Right now you don't have access to any majors")
        else:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="Right now you have access to the following majors \n" + message_list)
            self.access_list = access_list
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="To gain access to a new deadline manager ask your student rep for a one time password")
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Once generated use the command /password to gain access")
        return self.state.LOGIN
    async def login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        major = update.message.text
        if major in self.access_list:
            self.active_major = [major_name for major_name in majors.keys() if majors[major_name]["command"] == major][0]
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text=f"You have successfully logged in")
            self.update_hub()
            await self.major_hub.hub(update, context)
            return self.state.HUB
        else:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="That is not a valid choice, either you don't have access or it doesn't exist")
            return self.state.HOME

    def update_hub(self):
        """
        Update the info about the major name in all handlers
        """
        self.major_hub = Major_hub(self.active_major)
        self.login_handler.states[self.state.HUB] = [self.major_hub.major_handler]
    async def password_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="What is your one time password?")
        return self.state.VERIFICATION

    async def verify_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text
        major_name = password.split(':')[0]
        try:
            major_command = [key for key in majors.keys() if majors[key] == major_name][0]
        except IndexError:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Error: either you entered an incorrect password or one has not been generated")
            return self.state.HOME
        if not db.use_one_time_pass(password, major_name):
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Error: either you entered an incorrect password or one has not been generated")
            return self.state.HOME
        result = db.add_access_rights(update.effective_user, major_name, major_command)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Your rights have been successfully updated")
        return self.state.HOME

class Major_hub:
    def __init__(self, active_major):
        self.active_major = active_major
        self.state = Activity.HUB
        self.access_handler = Access_handler(active_major)
        self.deadline_handler = Deadline_handler(active_major)
        hub_handlers = [self.deadline_handler.deadline_handler,
                        self.access_handler.access_handler,
                        CommandHandler("logout", self.logout),
                        MessageHandler(filters.TEXT, self.hub)]
        self.major_handler=ConversationHandler(
            entry_points=hub_handlers,
            states={
                self.state.HUB: hub_handlers,
            },
            fallbacks=[MessageHandler(filters.TEXT, self.hub)],
            map_to_parent={
                self.state.HOME: self.state.HOME
            }
        )
    async def hub(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text=f"You are logged into {self.active_major}")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="From here you can add a /deadline or manage the /access")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="If you want to access other major /logout")
        return self.state.HUB

    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Successful logout")
        return self.state.HOME

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(DEADLINE_MANAGER_TOKEN).build()
    majors_hub = Majors_Login()
    application.add_handler(majors_hub.login_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()