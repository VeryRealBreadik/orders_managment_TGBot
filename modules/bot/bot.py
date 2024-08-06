import re

from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, PicklePersistence, ApplicationBuilder, CallbackQueryHandler,
)

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

CHOOSING_TABLE, PRE_ACTION, CREATING, READING, ACTIONS_WITH_CLIENTS, UPDATING, DELETING = range(7)


class Bot:
    def __init__(self, token: str, database):
        self.token = token
        self.persistence = PicklePersistence(filepath="mainbot.pkl")
        self.application = ApplicationBuilder().token(self.token).persistence(self.persistence).build()
        self.database = database
        self.page_limit = 10
        self.format_clients_output = lambda clients: "\n".join(str(client) for client in clients)
        self.format_orders_output = lambda orders: "\n".join(str(order) for order in orders) #  TODO: Доделать форматирование вывода данных
        self.paginator = {} #  Словарь содержащий ключ-пару MessageID-records_to_display. Нужен для хранения записей о клиентах/заказах для отдельных сообщений, в которых реализована возможность листать "страницы" таблицы

#  ---------------------------------------------------------------------------------------------------------------------
#  CONVERSATION HANDLER
    async def start(self):
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_cmd),
                MessageHandler(filters.Regex("^Вернуться$"), self.return_handler_function)
            ],
            states={
                CHOOSING_TABLE: [
                    MessageHandler(filters.Regex("^Клиенты$"), self.choose_action_over_clients_table)
                ],
                PRE_ACTION: [
                    MessageHandler(filters.Regex("^Добавить [А-Яа-яЁё]+$"), self.create_start),
                    MessageHandler(filters.Regex("^Просмотреть [А-Яа-яЁё]+$"), self.read_start),
                ],
                CREATING: [
                    MessageHandler(filters.Regex(r"^([А-Яа-яЁё]+\s([А-Яа-яЁё]+)\s[А-Яа-яЁё]+)\s(\d{11})$|^\d{2}\.\d{2}\.\d{4}\s\d+[\.|\,]?\d*\s(да|нет)i$"), self.create_records)
                ],
                READING: [
                    MessageHandler(filters.Regex(r"^\d+$|^[А-Яа-яЁё]+$"), self.read_clients_records),
                ],
                ACTIONS_WITH_CLIENTS: [

                ], #  TODO: Начать делать state для перехода к изменению записи о клиенте или заказе (также к просмотру и созданию заказа для отдельного клиента)
                UPDATING: [

                ],
                DELETING: [

                ] #  TODO: Начать делать states для обновления и удаления записей
            },
            fallbacks=[
                MessageHandler(filters.ALL, self.fallback)
            ],
            name="main_conversation",
            persistent=True,
            allow_reentry=True
        )
        page_handler = CallbackQueryHandler(self.page_buttons)
        self.application.add_handler(page_handler)
        self.application.add_handler(conv_handler)
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
#  TODO: Переделать архитекутуру бота. Уровни должны выглядеть следующим образом:
#  Выбрать таблицу (Clients/Orders) -> Выбрать действие (Create/Read) ->
#      Если Create -> Пользователь вводит данные клиента/заказа в нужном формате -> Продолжает создание записей о клиентах/заказах или возвращается назад
#      Если Read -> Пользователь ищет клиента/заказ по ID клиента/заказа, или по имени клиента, или по нужной неделе -> Если находит ОДНУ нужную запись о клиенте/заказе, пользователь выбирает действие с записью Update/Delete или вернуться назад ->
#          Если Update -> Пользователь вводит в нужном формате новые данные для данной записи -> Данные обновляются ->
#          Если Delete -> Запись удаляется из БД ->
#              Пользователя возвращают на поиск записи о клиенте/заказе

#  ---------------------------------------------------------------------------------------------------------------------
#  START
    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        user_data["states_deque"] = []
        reply_keyboard = [
            ["Клиенты"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
        await update.message.reply_text(
            "Посмотрим ваших клиентов?",
            reply_markup=markup,
        )

        return CHOOSING_TABLE

#  ---------------------------------------------------------------------------------------------------------------------
#  CRUD
#  CLIENTS ACTIONS
    async def choose_action_over_clients_table(self, update: Update, context: ContextTypes.DEFAULT_TYPE): #  TODO: Пересмотреть работу данной функции
        user_data = context.user_data
        user_data["current_table"] = "clients"

        records = self.database.get_clients()
        records_to_display = records[:self.page_limit]
        if records_to_display:
            reply_keyboard = [
                ["Добавить клиента", "Просмотреть клиента"]
            ]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
            await update.message.reply_text(
                "Добавить/просмотреть клиента?",
                reply_markup=markup,
            )
            inline_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="page_0"), InlineKeyboardButton("Вперёд", callback_data="page_2")]
            ])
            msg = await update.message.reply_text(
                f"{self.format_clients_output(records_to_display)}",
                reply_markup=inline_markup,
            )
            if len(self.paginator) > 2:
                del self.paginator[list(self.paginator.keys())[0]]
            self.paginator[msg.message_id] = records
        else:
            reply_keyboard = [
                ["Добавить клиента"],
                ["Вернуться"]
            ]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
            await update.message.reply_text(
                "База данных клиентов пуста, добавьте клиентов для начала работы",
                reply_markup=markup,
            )
        user_data["states_deque"].append(self.choose_action_over_clients_table)

        return PRE_ACTION

#  ---------------------------------------------------------------------------------------------------------------------
#  FALLBACKS
    async def fallback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "ERROR"
        )
        return await self.start_cmd(update, context)
#  TODO: Сделать более адекватные fallbacks для непредвиденных ситуаций

#  ---------------------------------------------------------------------------------------------------------------------
#  PRE-ACTIONS
    async def create_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        reply_keyboard = [
            ["Вернуться"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        if user_data["current_table"] == "clients":
            current_table_info_name = "клиента"
            current_table_info_format = "Фамилия Имя Отчество Номер телефона (например, 74951234567)"
        elif user_data["current_table"] == "orders":
            current_table_info_name = "заказа"
            current_table_info_format = "Дата заказа (например, 04.08.2024) Сумма заказа клиента (например, 2394.93) Оплачен заказ уже или нет (нет/да)"
        else:
            await update.message.reply_text(
                "Что-то пошло не так..."
            )
            return await self.start_cmd(update, context)

        await update.message.reply_text(
            f"Введите данные {current_table_info_name} в формате '{current_table_info_format}'",
            reply_markup=markup,
        )
        user_data["states_deque"].append(self.create_start)

        return CREATING

    async def read_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        reply_keyboard = [
            ["Вернуться"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Введите ID или имя клиента",
            reply_markup=markup,
        )
        user_data["states_deque"].append(self.read_start)

        return READING

    # async def update_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE): #  TODO: Кто я???
    #     user_data = context.user_data
    #     user_data["action"] = "client_update"
    #     reply_keyboard = [
    #         ["Вернуться"]
    #     ]
    #     markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    #     await update.message.reply_text(
    #         "Введите ID или имя клиента",
    #         reply_markup=markup,
    #     )
    #
    #     return TYPING #  TODO: TYPING больше нет, заменить на нужный впоследствии

    # async def delete_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE): #  TODO: Кто я???
    #     user_data = context.user_data
    #     user_data["action"] = "client_delete"
    #     reply_keyboard = [
    #         ["Вернуться"]
    #     ]
    #     markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    #     await update.message.reply_text(
    #         "Введите ID или имя клиента",
    #         reply_markup=markup,
    #     )
    #
    #     return TYPING #  TODO: TYPING больше нет, заменить на нужный впоследствии

#  ---------------------------------------------------------------------------------------------------------------------
#  TYPING TODO: TYPING больше нет, заменить на нужный впоследствии
    async def create_records(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        record_data = re.match(r"^([А-Яа-яЁё]+\s([А-Яа-яЁё]+)\s[А-Яа-яЁё]+)\s(\d{11})$|^(\d{2}[.,-]\d{2}[.,-]\d{4}) (\d+[.,]?\d*) (да|нет)i$", update.message.text)
        if user_data["current_table"] == "clients":
            record_data_dict = {"client_name": record_data[2], "client_fullname": record_data[1], "client_phone_number": record_data[3]}
            create_record_function = self.database.create_client
            info_name1 = "клиентов"
            info_name2 = "новых клиентов"
        elif user_data["current_table"] == "orders":
            record_data_dict = {"client_id": user_data["client_id"], "order_date": record_data[1], "order_sum": record_data[2], "order_payed": record_data[3]}
            create_record_function = self.database.create_order
            info_name1 = "заказов"
            info_name2 = "новые заказы"
        else:
            await update.message.reply_text(
                "Что-то пошло не так...",
            )
            return await self.start_cmd(update, context)

        try:
            create_record_function(record_data_dict)
            await update.message.reply_text(
                f"Данные добавлены успешно! Нажмите кнопку 'Вернуться', чтобы закончить добавление {info_name1} или продолжайте добавлять {info_name2} дальше",
            )
            user_data["states_deque"].pop()
            return await self.create_start(update, context)
        except Exception as e:
            await update.message.reply_text(
                f"Что-то пошло не так... Попробуйте ввести данные заново или нажмите кнопку 'Вернуться', чтобы закончить добавление {info_name1}",
            )
            user_data["states_deque"].pop()
            return await self.create_start(update, context)

    async def read_clients_records(self, update: Update, context: ContextTypes.DEFAULT_TYPE): #  TODO: Пересмотреть работу данной функции (возможны ошибки/недочёты при новой архитектуре), попытаться оптимизировать, сделать функции меньше
        user_data = context.user_data
        client_id = re.match(r"\d+", update.message.text)
        client_name = re.match(r"[А-Яа-яЁё]+", update.message.text)
        if client_id:
            records = [self.database.get_client_by_id(int(client_id[0]))]
            records_to_display = records
        elif client_name:
            records = self.database.get_clients_by_name(str(client_name[0]))
            records_to_display = records[:self.page_limit]
        else:
            await update.message.reply_text(
                "Что-то пошло не так..."
            )
            return await self.start_cmd(update, context)

        if not records_to_display:
            await update.message.reply_text(
                "Записи не найдены... Попробуйте найти клиента по другим данным или нажмите 'Вернуться'"
            )
            user_data["states_deque"].pop()
            return await self.read_start(update, context)
        if len(records) > self.page_limit:
            inline_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="page_0"),
                 InlineKeyboardButton("Вперёд", callback_data="page_2")]
            ])
            msg = await update.message.reply_text(
                f"{self.format_clients_output(records_to_display)}",
                reply_markup=inline_markup,
            )
            if len(self.paginator) > 2:
                del self.paginator[list(self.paginator.keys())[0]]
            self.paginator[msg.message_id] = records
            user_data["states_deque"].pop()
            return await self.read_start(update, context)
        else:
            await update.message.reply_text(
                f"{self.format_clients_output(records_to_display)}"
            ) #  TODO: Прикрутить кнопки под сообщение с ОДНОЙ записью о клиенте типа ["Обновить клиента", "Удалить клиента", "Просмотреть заказы клиента за последнюю неделю", "Просмотреть все заказы клиента"]
            user_data["states_deque"].pop()
            return await self.read_start(update, context)
#  TODO: После вывода результатов поиска по имени - убрать вариант найти человека по имени и вместо этого искать по ID с
#  TODO: выведенной информации в сообщении от бота. Также, когда найден один определённый клиент - дать выбор, что делать
#  TODO: с клиентом (обновить его, удалить, различные варианты просмотра его заказов). Далее - действия с заказами клиента...удачи...Лёха...

    async def update_record(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass
    
    async def delete_record(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

#  ---------------------------------------------------------------------------------------------------------------------
#  UTILITY FUNCTIONS
#  TODO: Оптимизировать большие функции с помощью utility функций, используемых только в основных функциях
    async def page_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data.startswith("page_"):
            page = int(query.data.split("_")[-1])
            records = self.paginator[query.message.message_id]
            records_to_display = records[(page - 1) * self.page_limit: page * self.page_limit]
            if records_to_display and page > 0:
                inline_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Назад", callback_data=f"page_{page - 1 if page > 0 else page}"), InlineKeyboardButton("Вперёд", callback_data=f"page_{page + 1 if page < len(records) / self.page_limit + (1 if len(records) % self.page_limit else 0) else page}")]
                ])
                await query.message.edit_text(
                    f"{self.format_clients_output(records_to_display)}",
                    reply_markup=inline_markup,
                )

    async def return_handler_function(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        states_deque = context.user_data["states_deque"]
        states_deque.pop()
        previous_state = states_deque.pop()
        return await previous_state(update, context)
