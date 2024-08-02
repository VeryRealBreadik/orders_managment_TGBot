import re
from typing import Dict

from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, PicklePersistence, ApplicationBuilder,
)

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

CHOOSING_TABLE, CRUD_CLIENTS, CRUD_ORDERS, TYPING = range(4)


class Bot:
    def __init__(self, token: str, database = None):
        self.token = token
        self.persistence = PicklePersistence(filepath="mainbot.pkl")
        self.application = ApplicationBuilder().token(self.token).persistence(self.persistence).build()
        self.database = database

    async def start(self):
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_cmd)],
            states={
                CHOOSING_TABLE: [
                    MessageHandler(filters.Regex("^Клиенты$"), self.crud_clients),
                    MessageHandler(filters.Regex("^Заказы$"), self.crud_orders)
                ],
                CRUD_CLIENTS: [
                    MessageHandler(filters.Regex("^Добавить клиента$"), self.add_client_start),
                    MessageHandler(filters.Regex("^Просмотреть клиента$"), self.read_client_start),
                    MessageHandler(filters.Regex("^Обновить клиента$"), self.update_client_start),
                    MessageHandler(filters.Regex("^Удалить клиента$"), self.delete_client_start)
                ],
                CRUD_ORDERS: [
                    MessageHandler(filters.Regex("^Добавить заказ$"), self.add_order_start),
                    MessageHandler(filters.Regex("^Просмотреть заказ$"), self.read_order_start),
                    MessageHandler(filters.Regex("^Обновить заказ$"), self.update_order_start),
                    MessageHandler(filters.Regex("^Удалить заказ$"), self.delete_order_start)
                ],
                TYPING: [
                    MessageHandler(filters.ALL & ~filters.COMMAND, self.perform_action_on_database)
                ]
            },
            fallbacks=[
                MessageHandler(filters.ALL, self.fallback)
            ],
            name="main_conversation",
            persistent=True,
            allow_reentry=True
        )
        self.application.add_handler(conv_handler)
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_keyboard = [
            ["Клиенты", "Заказы"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
        await update.message.reply_text(
            "Что делать?",
            reply_markup=markup,
        )

        return CHOOSING_TABLE

    async def crud_clients(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_keyboard = [
            ["Добавить клиента", "Просмотреть клиента"],
            ["Обновить клиента", "Удалить клиента"],
            ["Вернуться", ""]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "C, R, U или D?",
            reply_markup=markup,
        )

        return CRUD_CLIENTS

    async def crud_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE): #  TODO: Add some code to display a table to user
        reply_keyboard = [
            ["Добавить заказ", "Просмотреть заказ"],
            ["Обновить заказ", "Удалить заказ"],
            ["Вернуться", ""]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "C, R, U или D?",
            reply_markup=markup,
        )

        return CRUD_ORDERS

    async def fallback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Pizdec"
        )

    async def add_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "client_create"

        return TYPING

    async def read_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "client_read"

        return TYPING

    async def update_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "client_update"

        return TYPING

    async def delete_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "client_delete"

        return TYPING

    async def add_order_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "order_create"

        return TYPING

    async def read_order_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "order_read"

        return TYPING

    async def update_order_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "order_update"

        return TYPING

    async def delete_order_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "order_delete"

        return TYPING

    async def perform_action_on_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        if "action" not in user_data.keys():
            await update.message.reply_text(
                "Что-то пошло не так..."
            )
            return self.start_cmd(update, context)

        reply_keyboard = [
            ["Вернуться"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            '''Введите ваш запрос

            Подсказка:
            Формат ввода для добавления нового/обновления (если клиент уже выбран) клиента: "Иванов Иван Иванович 74951234567"
            Формат ввода для удаления/чтения/обновления (если клиент ещё не выбран) клиента: номер, соответствующий идентификатору (ID) клиента''',
            reply_markup=markup,
        )

        if user_data["action"] == "client_create":
            data = re.match(r"/^([А-Яа-яЁё]+\s([А-Яа-яЁё]+)\s[А-Яа-яЁё]+)\s(\d{11})$/gm", user_data["data"])
            if data:
                data_dict = {"client_name":data[1], "client_fullname":data[0], "client_phone_number":data[2]}
                self.database.create_client(data_dict)
            else:
                await  update.message.reply_text(
                    'Введённые данные не соответствуют формату ввода данных типа "Иванов Иван Иванович 74951234567", попробуйте ещё раз'
                )
                return #  TODO: Разобраться с return (чтобы пользователя отправляло заново вводить данные)
        elif user_data["action"] == "client_read":
            try:
                data_to_display = self.database.get_client_by_id(user_data["data"])
            except Exception as e:
                await update.message.reply_text(
                    f"Клиент с ID {user_data['data']} не найден, попробуйте ещё раз"
                )
                return  # TODO: Разобраться с return (чтобы пользователя отправляло заново вводить данные)
        elif user_data["action"] == "client_update":
            try:
                data_to_display = self.database.get_client_by_id(user_data["data"])
                user_data["client_id_to_update"] = user_data["data"]
            except Exception as e:
                await update.message.reply_text(
                    f"Клиент с ID {user_data['data']} не найден, попробуйте ещё раз"
                )
                return  # TODO: Разобраться с return (чтобы пользователя отправляло заново вводить данные)
        elif user_data["action"] == "client_delete":
            try:
                data_to_display = self.database.get_client_by_id(user_data["data"])
                reply_keyboard = [
                    ["Да", "Нет"]
                    ["Вернуться", ""]
                ]
                markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
                await update.message.reply_text(
                    f"Вы точно хотите удалить пользователя с ID {user_data['data']}?",
                    reply_markup=markup
                )
            except Exception as e:
                await update.message.reply_text(
                    f"Клиент с ID {user_data['data']} не найден, попробуйте ещё раз"
                )
                return  # TODO: Разобраться с return (чтобы пользователя отправляло заново вводить данные)
#  TODO: Разобраться полностью с функцией perform_action_on_database (посмотреть все return's, разобраться с тем, как должно всё выводиться пользователю и тд)
