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

# filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

CHOOSING_TABLE, CRUD_CLIENTS, CRUD_ORDERS, TYPING = range(4)


class Bot:
    def __init__(self, token: str, database = None):
        self.token = token
        print("g")
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
                    # MessageHandler(filters.Regex("^Добавить клиента$"), self.add_client_start),
                    # MessageHandler(filters.Regex("^Просмотреть клиента$"), self.read_client_start),
                    # MessageHandler(filters.Regex("^Обновить клиента$"), self.update_client_start),
                    # MessageHandler(filters.Regex("^Удалить клиента$"), self.delete_client_start)
                ],
                CRUD_ORDERS: [

                ]
            },
            fallbacks=[
                MessageHandler(filters.ALL, self.fallback)
            ],
            name="main_conversation",
            persistent=True,
            allow_reentry=True
        )
        print("Rawr1")
        self.application.add_handler(conv_handler)
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        print("Rawr")

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_keyboard = [
            ["Orders", "Clients"]
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

    async def crud_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
