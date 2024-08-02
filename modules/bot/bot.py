import re
from typing import Dict

from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, PicklePersistence, ApplicationBuilder, CallbackQueryHandler,
)

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

CHOOSING_TABLE, CRUD_CLIENTS, CRUD_ORDERS, TYPING = range(4)


class Bot:
    def __init__(self, token: str, database):
        self.token = token
        self.persistence = PicklePersistence(filepath="mainbot.pkl")
        self.application = ApplicationBuilder().token(self.token).persistence(self.persistence).build()
        self.database = database
        self.page_limit = 10
        self.format_clients_output = lambda clients: "\n".join(str(client) for client in clients)
        self.format_orders_output = lambda orders: "\n".join(str(order) for order in orders) #  TODO: Доделать форматирование вывода данных

#  ---------------------------------------------------------------------------------------------------------------------
#  CONVERSATION HANDLER
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
                    MessageHandler(filters.Regex("^Удалить клиента$"), self.delete_client_start),
                    MessageHandler(filters.Regex("^Вернуться$"), self.start_cmd),
                    CallbackQueryHandler(self.clients_page_buttons)
                ],
                CRUD_ORDERS: [
                    MessageHandler(filters.Regex("^Добавить заказ$"), self.add_order_start),
                    MessageHandler(filters.Regex("^Просмотреть заказ$"), self.read_order_start),
                    MessageHandler(filters.Regex("^Обновить заказ$"), self.update_order_start),
                    MessageHandler(filters.Regex("^Удалить заказ$"), self.delete_order_start),
                    MessageHandler(filters.Regex("^Вернуться$"), self.start_cmd),
                    CallbackQueryHandler(self.orders_page_buttons)
                ],
                TYPING: [
                    MessageHandler(filters.ALL & ~filters.COMMAND, self.perform_action_on_database) #  TODO: сделать возврат на уровень вверх по кнопке "Вернуться"
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

#  ---------------------------------------------------------------------------------------------------------------------
#  START
    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_keyboard = [
            ["Клиенты", "Заказы"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
        await update.message.reply_text(
            "Что делать?",
            reply_markup=markup,
        )

        return CHOOSING_TABLE

#  ---------------------------------------------------------------------------------------------------------------------
#  CRUD
#  CLIENTS CRUD
    async def crud_clients(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["current_table"] = "clients"

        clients = self.database.get_clients()[:self.page_limit]
        if clients:
            reply_keyboard = [
                ["Добавить клиента", "Просмотреть клиента"],
                ["Обновить клиента", "Удалить клиента"],
                ["Вернуться", ""]
            ]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Добавить/просмотреть/обновить/удалить клиента?",
                reply_markup=markup,
            )
            inline_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="page_1"), InlineKeyboardButton("Вперёд", callback_data="page_2")]
            ])
            await update.message.reply_text(
                f"{self.format_clients_output(clients)}",
                reply_markup=inline_markup,
            )
        else:
            reply_keyboard = [
                ["Добавить клиента"],
                ["Вернуться"]
            ]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "База данных клиентов пуста, добавьте клиентов для начала работы",
                reply_markup=markup,
            )

        return CRUD_CLIENTS

    async def clients_page_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data.startswith("page_"):
            page = int(query.data.split("_")[-1])
            clients = self.database.get_clients()
            clients_on_current_page = clients[(page - 1) * self.page_limit: page * self.page_limit]
            inline_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data=f"page_{page - 1 if page > 1 else page}"), InlineKeyboardButton("Вперёд", callback_data=f"page_{page + 1 if page < len(clients) / self.page_limit + (1 if len(clients) % self.page_limit else 0) else page}")]
            ])
            await query.message.edit_text(
                f"{self.format_clients_output(clients_on_current_page)}",
                reply_markup=inline_markup,
            )

#  ---------------------------------------------------------------------------------------------------------------------
#  ORDERS CRUD
    async def crud_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["current_table"] = "orders"

        orders = self.database.get_orders_by_week()[:self.page_limit]
        if orders:
            reply_keyboard = [
                ["Добавить заказ", "Просмотреть заказ"],
                ["Обновить заказ", "Удалить заказ"],
                ["Вернуться", ""]
            ]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Добавить/просмотреть/обновить/удалить заказ?",
                reply_markup=markup,
            )
            inline_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="page_1"),
                 InlineKeyboardButton("Вперёд", callback_data="page_2")]
            ])
            await update.message.reply_text(
                f"{self.format_clients_output(orders)}",
                reply_markup=inline_markup,
            )
        else:
            reply_keyboard = [
                ["Добавить заказ"],
                ["Вернуться"]
            ]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "База данных заказов пуста, добавьте заказы для начала работы",
                reply_markup=markup,
            )

        return CRUD_ORDERS

    async def orders_page_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data.startswith("page_"):
            page = int(query.data.split("_")[-1])
            orders = self.database.get_orders_by_week()
            orders_on_current_page = orders[(page - 1) * self.page_limit: page * self.page_limit]
            inline_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data=f"page_{page - 1 if page > 1 else page}"),
                 InlineKeyboardButton("Вперёд",
                                      callback_data=f"page_{page + 1 if page < len(orders) / self.page_limit + (1 if len(orders) % self.page_limit else 0) else page}")]
            ])
            await query.message.edit_text(
                f"{self.format_clients_output(orders_on_current_page)}",
                reply_markup=inline_markup,
            )

#  ---------------------------------------------------------------------------------------------------------------------
#  FALLBACKS
    async def fallback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Pizdec"
        )

#  ---------------------------------------------------------------------------------------------------------------------
#  CRUD ACTIONS
#  CLIENTS ACTIONS
    async def add_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "client_create"
        reply_keyboard = [
            ["Вернуться"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Введите данные клиента в формате 'Иванов Иван Иванович 74951234567'",
            reply_markup=markup,
        )

        return TYPING

    async def read_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "client_read"
        reply_keyboard = [
            ["Вернуться"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Введите ID или имя клиента",
            reply_markup=markup,
        )

        return TYPING

    async def update_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "client_update"
        reply_keyboard = [
            ["Вернуться"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Введите ID или имя клиента",
            reply_markup=markup,
        )

        return TYPING

    async def delete_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["action"] = "client_delete"
        reply_keyboard = [
            ["Вернуться"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Введите ID или имя клиента",
            reply_markup=markup,
        )

        return TYPING

#  ---------------------------------------------------------------------------------------------------------------------
#  ORDERS ACTIONS TODO: доделать как CLIENTS CRUD
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

#  ---------------------------------------------------------------------------------------------------------------------
#  TYPING
    async def perform_action_on_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        if "action" not in user_data.keys():
            await update.message.reply_text(
                "Что-то пошло не так..."
            )
            return self.start_cmd(update, context)
        user_data["data"] = update.message.text
        if user_data["action"] == "client_create":
            client_data = re.match(r"^([А-Яа-яЁё]+\s([А-Яа-яЁё]+)\s[А-Яа-яЁё]+)\s(\d{11})$", user_data["data"])
            if client_data:
                client_data_dict = {"client_name": client_data[2], "client_fullname": client_data[1], "client_phone_number": client_data[3]}
                try:
                    self.database.create_client(client_data_dict)
                    await update.message.reply_text(
                        "Данные добавлены успешно! Нажмите кнопку 'Вернуться', чтобы закончить добавление клиентов или продолжайте добавлять новых клиентов дальше",
                    )
                    return TYPING
                except Exception as e:
                    await update.message.reply_text(
                        f"Что-то пошло не так... Попробуйте ввести данные заново или нажмите кнопку 'Вернуться', чтобы закончить добавление клиентов. ОШИБКА {e}",
                    )
                    return await self.add_client_start(update, context)
            else:
                await update.message.reply_text(
                    "Неверный формат ввода данных клиента, повторите ввод данных",
                )
                return await self.add_client_start(update, context)

#  TODO: Разобраться полностью с функцией perform_action_on_database (доделать client_create и начать делать остальные)
