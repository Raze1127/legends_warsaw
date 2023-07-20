from time import sleep
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton, \
    InputMediaPhoto, LabeledPrice
from telegram.error import NetworkError
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters, \
    ConversationHandler
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import requests

# Firebase initialization
cred = credentials.Certificate("legendswarsaw-firebase-adminsdk-9d5pd-7c39f1e9c3.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://legendswarsaw-default-rtdb.europe-west1.firebasedatabase.app/"
})
ref = db.reference("/")
chatID = 0


# Стартовый обработчик
def start(update: Update, context: CallbackContext) -> None:
    username = update.effective_user.first_name
    chatid = update.effective_chat.id
    user = ref.child("Users").child(f'{chatid}').get()
    if user is not None:
        context.user_data['language'] = user['language']
        context.user_data['region'] = 'region1'
        send_main_menu(update, context)
        return
    update.message.reply_text(f'Привет, {username}!')
    ref.child("Users").child(f'{chatid}').update({
        'name': username,
        'username': update.effective_user.username,
    })
    keyboard = [
        [InlineKeyboardButton("Русский", callback_data='russian'),
         InlineKeyboardButton("Українська🇺🇦", callback_data='ukranian')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Выберете язык:', reply_markup=reply_markup)


# Обработчик выбора языка
def button_lang(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    context.user_data['language'] = query.data
    if query.data == 'russian':
        text = 'Вы выбрали Русский язык, позже будет возможно это поменять.'
        keyboard = [
            [InlineKeyboardButton("Регион 1", callback_data='region1'),
             InlineKeyboardButton("Регион 2", callback_data='region2')]
        ]
        ref.child("Users").child(f'{update.effective_chat.id}').update({
            'language': 'russian'
        })
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text=text)
        request_phone_number(update, context)

    if query.data == 'ukranian':
        text = 'Ви вибрали українську мову, пізніше буде можливо це поміняти.'
        ref.child("Users").child(f'{update.effective_chat.id}').update({
            'language': 'ukranian'
        })
        keyboard = [
            [InlineKeyboardButton("Регіон 1", callback_data='region1'),
             InlineKeyboardButton("Регіон 2", callback_data='region2')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text=text)
        request_phone_number(update, context)


# Обработчик выбора региона
def button_region(update: Update, context: CallbackContext) -> None:
    # global text
    # query = update.callback_query
    # query.answer()
    # context.user_data['region'] = query.data
    #
    # ref.child("Users").child(f'{update.effective_chat.id}').update({
    #     'region': context.user_data['region']
    # })
    # if query.data == 'region1':
    #     text = 'Вы выбрали Регион 1.' if context.user_data['language'] == 'russian' else 'Ви вибрали Регіон 1.'
    # if query.data == 'region2':
    #     text = 'Вы выбрали Регион 2.' if context.user_data['language'] == 'russian' else 'Ви вибрали Регіон 2.'
    # query.edit_message_text(text=text)
    request_phone_number(update, context)


# Запрос номера телефона
def request_phone_number(update: Update, context: CallbackContext):
    phone_keyboard = KeyboardButton(
        text="Отправить номер телефона" if context.user_data['language'] == 'russian' else "Надіслати номер телефону",
        request_contact=True)
    cancel_keyboard = KeyboardButton(text="Отмена" if context.user_data['language'] == 'russian' else "Скасувати")
    custom_keyboard = [[phone_keyboard], [cancel_keyboard]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Пожалуйста, поделитесь своим номером телефона." if context.user_data[
                                                                                          'language'] == 'russian' else "Будь ласка, поділіться своїм номером телефону.",
                             reply_markup=reply_markup)


# Обработчик номера телефона
def phone_number_handler(update: Update, context: CallbackContext):
    contact = update.message.contact
    chatid = update.effective_chat.id
    ref.child("Users").child(f'{chatid}').update({
        'phone_number': contact.phone_number
    })
    send_main_menu(update, context)
    handle_schedule(update, context)



# Отправка главного меню
def send_main_menu(update: Update, context: CallbackContext) -> None:
    language = context.user_data.get('language', 'russian')
    text = 'Главное меню' if language == 'russian' else 'Головне меню'
    keyboard = [
        ['Задать вопрос', 'Профиль'] if language == 'russian' else ['Задати питання', 'Профіль'],
        ['Регистрации', 'Расписание'] if language == 'russian' else ['Реєстраціі', 'Розклад'],
        ['Презентация', "Курс криптовалют"] if language == 'russian' else ['Презентація', "Курс криптовалют"],
    ]
    context.user_data['qna'] = False
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)


ADMIN_CHAT_ID = 1149173006
QNA = 0


def handle_question(update: Update, context: CallbackContext):
    language = context.user_data.get('language', 'russian')
    text = 'Введите ваш вопрос:' if language == 'russian' else 'Введіть своє запитання:'
    keyboard = [
        ['отмена'] if language == 'russian' else ['скасувати'],
    ]
    context.user_data['qna'] = True
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)


# Обработчик введенного вопроса
def question_text_handler(update: Update, context: CallbackContext):
    question = update.message.text
    language = context.user_data.get('language', 'russian')
    text = 'Вопрос отправлен! Ответ поступит вам в данный чат.' if language == 'russian' else 'Питання відправлено! Відповідь надійде вам в даний чат.'
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=text)
    context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f'Вопрос от {update.effective_user.first_name}: {question}')
    send_main_menu(update, context)



def handle_profile(update: Update, context: CallbackContext):
    language = context.user_data.get('language', 'russian')
    text = 'Профиль' if language == 'russian' else 'Профіль'
    keyboard = [
        # ["Изменить регион" if language == 'russian' else "Змінити регіон"],
        ["Изменить язык" if language == 'russian' else "Змінити мову"],
        ["Главное меню" if language == 'russian' else "Головне меню"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)


def change_region(update: Update, context: CallbackContext):
    language = context.user_data.get('language', 'russian')
    text = "Выберите регион:" if language == 'russian' else "Виберіть регіон:"
    keyboard = [
        [InlineKeyboardButton("Регион 1" if language == 'russian' else "Регіон 1", callback_data='regionchange1')],
        [InlineKeyboardButton("Регион 2" if language == 'russian' else "Регіон 2", callback_data='regionchange2')],
        [InlineKeyboardButton("Отмена" if language == 'russian' else "Скасувати", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)


# def button_change_region(update: Update, context: CallbackContext) -> None:
#     global text
#     query = update.callback_query
#     query.answer()
#     language = context.user_data.get('language', 'russian')
#
#     if query.data == 'cancel':
#         handle_profile(update, context)
#     else:
#         context.user_data['region'] = query.data.replace('change', '')
#
#         ref.child("Users").child(f'{update.effective_chat.id}').update({
#             'region': context.user_data['region']
#         })
#         if query.data == 'regionchange1':
#             text = 'Вы выбрали Регион 1.' if language == 'russian' else 'Ви вибрали ' \
#                                                                         'Регіон 1.'
#
#         if query.data == 'regionchange2':
#             text = 'Вы выбрали Регион 2.' if language == 'russian' else 'Ви вибрали ' \
#                                                                         'Регіон 2.'
#         query.edit_message_text(text=text)
#         handle_profile(update, context)


def change_language(update: Update, context: CallbackContext) -> None:
    current_language = context.user_data.get('language', 'russian')  # Default to 'russian' if no language set
    text = 'Выбран язык: Русский' if current_language == 'russian' else 'Обрана мова: Українська'

    keyboard = [
        [InlineKeyboardButton("Русский", callback_data='russianchange')],
        [InlineKeyboardButton("Українська", callback_data='ukrainianchange')],
        [InlineKeyboardButton("Отмена" if current_language == 'russian' else "Скасувати",
                              callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)


def crypto_rates(update: Update, context: CallbackContext) -> None:
    # Define the cryptocurrencies to fetch
    cryptocurrencies = ["bitcoin", "ethereum", "binancecoin", "solana"]

    # Create a mapping of full names to abbreviations
    crypto_names = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "binancecoin": "BNB",
        "solana": "SOL"
    }

    # Make a GET request to CoinGecko API
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(cryptocurrencies)}&vs_currencies=usd"
    response = requests.get(url)
    data = response.json()

    # Extract the prices
    prices = {crypto_names[crypto]: data[crypto]["usd"] for crypto in cryptocurrencies}

    # Construct the message text
    text = ""
    for crypto, price in prices.items():
        text += f"{crypto}: ${price}\n"

    # Send the message
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def presentation(update: Update, context: CallbackContext) -> None:
    text = ""

    # Send the message
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def button_change_language(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    context.user_data['language'] = query.data.replace('change', '')  # Save the chosen language in user data
    ref.child("Users").child(f'{update.effective_chat.id}').update({
        'language': context.user_data['language']
    })
    if query.data == 'russianchange':
        query.edit_message_text('Вы выбрали Русский язык.')
        handle_profile(update, context)
    elif query.data == 'ukrainianchange':
        query.edit_message_text('Ви вибрали українську мову.')
        handle_profile(update, context)


def handle_schedule(update: Update, context: CallbackContext):
    # If there is no current event index for the user, start from the first one
    context.user_data.setdefault('current_event_index', 1)
    ref = firebase_admin.db.reference()
    # Load the events for the user's region
    region = context.user_data.get('region', 'region1')
    events = ref.child("schedule").child(region).get()
    current_language = context.user_data.get('language', 'russian')

    if not events:
        update.message.reply_text("Нет ближайших событий")
        return
        events.pop(0)
    if context.user_data['current_event_index'] >= len(events):
        context.user_data['current_event_index'] = 1

    # Get the current event
    event = events[context.user_data['current_event_index']]
    print(len(events))
    print(context.user_data['current_event_index'])
    print(events)
    # Create a keyboard with navigation and registration buttons
    keyboard = [
        [InlineKeyboardButton("⬅️", callback_data='previous_event'),
         InlineKeyboardButton("Регистрация" if current_language == 'russian' else "Реєстрація",
                              callback_data='register'),
         InlineKeyboardButton("➡️", callback_data='next_event')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    name = event['name']
    date = event['date']
    place = event['place']
    text_event = event['text']

    # Send the event information to the user
    update.message.reply_text("Ближайшие события:" if current_language == 'russian' else "Найближчі події:")
    context.bot.send_photo(chat_id=update.effective_chat.id,
                           photo=event['photo'],
                           caption=f'{name}\n{text_event}\n\n📆{date}\n📍{place}',
                           reply_markup=reply_markup)


def handle_event_navigation(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    current_language = context.user_data.get('language', 'russian')

    # Load the events for the user's region
    region = context.user_data.get('region', 'region1')
    events = ref.child("schedule").child(region).get()
    if not events:
        query.edit_message_text(
            "Нет ближайших событий." if current_language == 'russian' else "Немає найближчих подій.")
        return

    # Determine the number of events
    num_events = len(events) - 1  # Subtract 1 because of 0-indexing

    if query.data == 'next_event':
        # Go to the next event, but don't exceed the total number of events
        if num_events == context.user_data['current_event_index']:
            context.user_data['current_event_index'] = 1
        else:
            context.user_data['current_event_index'] = context.user_data['current_event_index'] + 1

    elif query.data == 'previous_event':
        # Go to the previous event, but don't go below the first one
        if context.user_data['current_event_index'] == 1:
            context.user_data['current_event_index'] = num_events
        else:
            context.user_data['current_event_index'] = context.user_data['current_event_index'] - 1
    # Get the current event
    event = events[context.user_data['current_event_index']]

    # Create a keyboard with navigation and registration buttons
    keyboard = [
        [InlineKeyboardButton("⬅️", callback_data='previous_event'),
         InlineKeyboardButton("Регистрация", callback_data='register'),
         InlineKeyboardButton("➡️", callback_data='next_event')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    name = event['name']
    date = event['date']
    place = event['place']
    text_event = event['text']
    # Update the message with the new event
    query.edit_message_media(
        media=InputMediaPhoto(media=event['photo'], caption=f'{name}\n{text_event}\n\n📆{date}\n📍{place}'),
        reply_markup=reply_markup)


def handle_registration(update: Update, context: CallbackContext):
    current_language = context.user_data.get('language', 'russian')
    chat_id = update.effective_chat.id
    event = context.user_data.get('current_event_index')
    print(event)
    region = context.user_data.get('region', 'region1')
    eventbase = ref.child("schedule").child(region).child(str(event)).get()
    user = ref.child("Users").child(str(update.effective_chat.id)).get()

    keyboard = [
        [
            InlineKeyboardButton("Оплатить" if current_language == 'russian' else "Оплатити", url=(eventbase['pricelink']))]
    ]

    keyboard2 = [
        [InlineKeyboardButton("Подтвердить оплату", callback_data='approve')],
        [InlineKeyboardButton("Отклонить оплату", callback_data='notapprove')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    reply_markup2 = InlineKeyboardMarkup(keyboard2)
    name = user['name']
    phone = user.get('phone_number', '')

    language = context.user_data.get('language', 'russian')
    if not phone:
        phone=""
    messages = {
        'russian': f'Ваши данные для регистрации: \n'
                   f'Имя: {name}\n'
                   f'Телефон: {phone}\n'
                   f'Чтобы зарегистрироваться на событие, пожалуйста, оплатите по кнопке ниже.',

        'ukrainian': f'Ваші дані для реєстрації: \n'
                     f'Ім\'я: {name}\n'
                     f'Телефон: {phone}\n'
                     f'Щоб зареєструватися на подію, будь ласка, оплатіть за допомогою кнопки нижче.'
    }

    ref.child("Users").child(f'{update.effective_chat.id}').child('registers').update({
        eventbase['name']: 0
    })
    context.bot.send_message(
        ADMIN_CHAT_ID,
        text=f"Проверьте оплату пользователя {update.effective_user.first_name}, на событие {eventbase['name']}, "
             f"регион: {region}, Тех. данные:[{region},{update.effective_chat.id},{str(event)},{eventbase['name']}]",
        reply_markup=reply_markup2
    )


    context.bot.send_message(
        chat_id,
        text=messages[language],
        reply_markup=reply_markup
    )


def view_stats(update: Update, context: CallbackContext):
    ref = firebase_admin.db.reference()  # replace this with your own Firebase reference

    # Получить всех пользователей
    users = ref.child('Users').get()
    num_users = len(users)

    # Получить все регионы и посчитать количество событий в каждом
    regions = ref.child('schedule').get()
    num_events_per_region = {region: len(events) for region, events in regions.items()}

    # Посчитать количество регистраций на каждое событие
    num_regs_per_event = {}
    for region, events in regions.items():
        for event in events:
            if event is not None and 'registers' in event:
                event_name = event['name']
                num_regs = len(event['registers'])
                num_regs_per_event[event_name] = num_regs

    # Форматировать статистику в виде строки
    stats_str = f'Количество пользователей: {num_users}\n'
    stats_str += 'Количество событий по регионам:\n'
    for region, num_events in num_events_per_region.items():
        stats_str += f'  {region}: {num_events}\n'
    stats_str += 'Количество регистраций на каждое событие:\n'
    for event_name, num_regs in num_regs_per_event.items():
        stats_str += f'  {event_name}: {num_regs}\n'

    # Отправить статистику пользователю
    context.bot.send_message(chat_id=update.effective_chat.id, text=stats_str)


def current_registrations(update: Update, context: CallbackContext):
    user_chat_id = str(update.effective_chat.id)
    ref = db.reference(f"Users/{user_chat_id}/registers")
    registrations = ref.get()
    current_language = context.user_data.get('language', 'russian')

    if not registrations:
        update.message.reply_text(
            "Вы еще не зарегистрировались на события." if current_language == 'russian' else "Ви ще не зареєструвалися на події.")
        return

    paid_registrations = [(name, status) for name, status in registrations.items() if status == 2]

    if not paid_registrations:
        update.message.reply_text(
            "У вас нет оплаченных регистраций." if current_language == 'russian' else "У вас немає оплачених реєстрацій.")
        return

    ref_schedule = db.reference(f"schedule")
    regions = ref_schedule.get().keys()

    response = ''
    for region in regions:
        region_events = ref_schedule.child(region).get()
        for event_name, event_status in paid_registrations:
            for event in region_events:
                if event and event['name'] == event_name:
                    if current_language == 'russian':
                        response += f"\n\nСобытие: {event['name']}\nДата: {event['date']}\nМесто: {event['place']}"
                    else:
                        response += f"\n\nПодія: {event['name']}\nДата: {event['date']}\nМісце: {event['place']}"

    if current_language == 'russian':
        update.message.reply_text("Ваши оплаченные регистрации:" + response)
    else:
        update.message.reply_text("Ваші оплачені реєстрації:" + response)


def admin_login(update: Update, context: CallbackContext):
    context.user_data['is_admin'] = True

    keyboard = [
        [KeyboardButton('Добавить событие')],
        [KeyboardButton('Удалить событие')],
        [KeyboardButton('Статистика')],
        [KeyboardButton('Текущие события')],
        [KeyboardButton('Войти в обычный аккаунт')],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Вы вошли как администратор.',
        reply_markup=reply_markup
    )


def handle_approve(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    parts = query.message.text.split("Тех. данные:")

    # Теперь parts[1] содержит технические данные
    tech_data = parts[1]

    # Удаляем скобки [ и ]
    tech_data = tech_data.replace('[', '').replace(']', '')

    # Разделяем технические данные по запятой
    region, chat_id, event_number, event_name = tech_data.split(',')

    ref.child("Users").child(chat_id).child('registers').update({
        event_name: 2
    })
    ref.child("schedule").child(region).child(str(event_number)).child('registers').push(chat_id)

    query.edit_message_text('Оплата подтверждена.')

    context.bot.send_message(
        chat_id,
        text='Ваша регистрация на событие подтверждена. Спасибо за оплату!'
    )


def handle_notapprove(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    parts = query.message.text.split("Тех. данные:")

    tech_data = parts[1]

    tech_data = tech_data.replace('[', '').replace(']', '')

    region, chat_id, event_number, event_name = tech_data.split(',')

    ref.child("Users").child(chat_id).child('registers').update({
        event_name: -1
    })

    query.edit_message_text('Оплата отклонена.')

    context.bot.send_message(
        chat_id,
        text='К сожалению, ваша регистрация на событие была отклонена. Пожалуйста, свяжитесь с администратором для '
             'получения дополнительной информации.'
    )


NAME, DESCRIPTION, LOCATION, DATE, PHOTO, PRICE, PRICELINK, REGION = range(8)


def add_event(update: Update, context: CallbackContext):
    update.message.reply_text('Введите название события:')
    return NAME


def handle_name(update: Update, context: CallbackContext):
    context.user_data['event_name'] = update.message.text
    update.message.reply_text('Введите описание события:')
    return DESCRIPTION


def handle_description(update: Update, context: CallbackContext):
    context.user_data['event_description'] = update.message.text
    update.message.reply_text('Введите место события:')
    return LOCATION


def handle_location(update: Update, context: CallbackContext):
    context.user_data['event_location'] = update.message.text
    update.message.reply_text('Введите дату события:')
    return DATE


def handle_date(update: Update, context: CallbackContext):
    context.user_data['event_date'] = update.message.text
    update.message.reply_text('Загрузите фото события:')
    return PHOTO


def handle_photo(update: Update, context: CallbackContext):
    context.user_data['event_photo'] = update.message.photo[-1].file_id
    update.message.reply_text('Введите цену билета:')
    return PRICELINK

def handle_payment(update: Update, context: CallbackContext):
    context.user_data['event_price'] = update.message.text
    update.message.reply_text('Отправьте ссылку для оплаты:')
    return PRICE


def handle_price(update: Update, context: CallbackContext):
    context.user_data['event_pricelink'] = update.message.text

    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton("Варшава", callback_data='region1')],

    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Выберите регион:', reply_markup=reply_markup)
    return REGION


def handle_region(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    context.user_data['event_region'] = query.data

    # Здесь вы должны сохранить данные в базе данных
    event_name = context.user_data['event_name']
    event_description = context.user_data['event_description']
    event_location = context.user_data['event_location']
    event_date = context.user_data['event_date']
    event_photo = context.user_data['event_photo']
    event_price = context.user_data['event_price']
    event_region = context.user_data['event_region']
    event_pricelink = context.user_data["event_pricelink"]
    # Save the data to your database

    # Creating inline buttons for saving or canceling
    keyboard = [
        [InlineKeyboardButton("Сохранить", callback_data='save')],
        [InlineKeyboardButton("Отменить", callback_data='cancel')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Showing preview of the event before adding it
    context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=event_photo,
        caption=f'{event_name}\n{event_description}\n\n📆{event_date}\n📍{event_location}',
        reply_markup=reply_markup
    )

    return REGION  # We return REGION again to wait for user to decide either to save or cancel


def handle_save(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Save the event to your database here
    keyboard = [
        [KeyboardButton('Добавить событие')],
        [KeyboardButton('Удалить событие')],
        [KeyboardButton('Статистика')],
        [KeyboardButton('Текущие события')],
        [KeyboardButton('Войти в обычный аккаунт')],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    event_name = context.user_data['event_name']
    event_description = context.user_data['event_description']
    event_location = context.user_data['event_location']
    event_date = context.user_data['event_date']
    event_photo = context.user_data['event_photo']
    event_price = context.user_data['event_price']
    event_region = context.user_data['event_region']
    event_pricelink = context.user_data["event_pricelink"]

    ref = firebase_admin.db.reference()  # replace this with your own Firebase reference
    num_events = 1
    events = ref.child("schedule").child(event_region).get()
    if not events:
        pass
    else:
        num_events = len(events)

    new_event = {
        "name": event_name,
        "text": event_description,
        "place": event_location,
        "date": event_date,
        "photo": event_photo,
        "price": event_price,
        "pricelink": event_pricelink
    }
    ref.child("schedule").child(event_region).child(str(num_events)).update(new_event)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Событие успешно добавлено',
        reply_markup=reply_markup
    )

    ref = firebase_admin.db.reference('Users')
    users = ref.get()

    keyboard2 = [
        [InlineKeyboardButton("Регистрация", url=event_pricelink)]
    ]
    reply_markup2 = InlineKeyboardMarkup(keyboard2)
    context.user_data['current_event_index'] = num_events
    context.user_data['current_event_index'] = num_events
    i=1
    for user_id, user_data in users.items():
            print(i)
            i= i+1
            context.bot.send_photo(
                chat_id=int(user_id),
                photo=event_photo,
                caption=f'{str(event_name)}\n{str(event_description)}\n\n📆{str(event_date)}\n📍{str(event_location)}',
            )

    return ConversationHandler.END


def handle_cancel(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Clear temporary data
    context.user_data.clear()

    keyboard = [
        [KeyboardButton('Добавить событие')],
        [KeyboardButton('Удалить событие')],
        [KeyboardButton('Статистика')],
        [KeyboardButton('Текущие события')],
        [KeyboardButton('Войти в обычный аккаунт')],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Добавление события отменено.',
        reply_markup=reply_markup
    )
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    context.user_data.clear()
    update.message.reply_text('Добавление события отменено.')
    return ConversationHandler.END


def delete_event(update: Update, context: CallbackContext):
    ref = firebase_admin.db.reference()  # replace this with your own Firebase reference

    # Get a list of regions from Firebase
    regions = ref.child('schedule').get()
    if regions is not None:
        regions = regions.keys()

    if regions:
        # Create a button for each region
        keyboard = [[InlineKeyboardButton(region, callback_data=f'Warsaw')] for region in regions]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Выберите регион для удаления события:',
            reply_markup=reply_markup
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Нет доступных событий.'
        )


def handle_region_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Extract the region from the callback data
    region = query.data.split('_')[1]

    # Store the selected region in user_data for later use
    context.user_data['region'] = region

    ref = firebase_admin.db.reference()  # replace this with your own Firebase reference
    events = ref.child('schedule').child(region).get()

    if events:
        # Create a button for each event

        keyboard = [[InlineKeyboardButton(event['name'], callback_data=f'delete_{i}')]
                    for i, event in enumerate(events) if event is not None]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            'Выберите событие для удаления:',
            reply_markup=reply_markup
        )
    else:
        query.edit_message_text('В этом регионе нет событий.')


def handle_delete(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    # Extract the event number from callback_data
    event_number = int(query.data.split('_')[1])

    ref = firebase_admin.db.reference()  # replace this with your own Firebase reference
    region = context.user_data.get('region', 'region1')  # get the current region from user_data
    events = ref.child('schedule').child(region).get()

    # Delete the selected event and re-index the remaining events
    event_to_delete = ref.child('schedule').child(region).child(str(event_number)).get()

    del events[event_number]
    for i in range(event_number, len(events)):
        ref.child('schedule').child(region).child(str(i)).set(events[i])

    # Delete the last event in the Firebase
    ref.child('schedule').child(region).child(str(len(events))).delete()

    # Remove event from users' registers
    users = ref.child('Users').get()
    event_name = event_to_delete['name']
    for user_id, user_data in users.items():
        if 'registers' in user_data and event_name in user_data['registers']:
            ref.child('Users').child(user_id).child('registers').child(event_name).delete()

    query.edit_message_text('Событие успешно удалено.')
    return ConversationHandler.END


def text_handler(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    if context.user_data.get('is_admin', False):
        if text in ['войти в обычный аккаунт']:
            context.user_data['is_admin'] = False
            send_main_menu(update, context)
        elif text == 'удалить событие':
            delete_event(update, context)
        elif text == 'текущие события':
            handle_schedule(update, context)
        elif text in ['статистика']:
            view_stats(update, context)

    else:
        if text in ['отмена', 'скасувати']:
            send_main_menu(update, context)
        elif text in ['задать вопрос', 'задати питання']:
            handle_question(update, context)
        elif text in ['adminislegend']:
            admin_login(update, context)
        elif text == 'курс криптовалют':
            crypto_rates(update, context)
        elif text == 'курс криптовалют':
            crypto_rates(update, context)
        elif text in ['презентация', 'презентація']:
            presentation(update, context)
        elif text in ['профиль', 'профіль']:
            handle_profile(update, context)
        elif text in ['регистрация', 'реєстрація']:
            handle_registration(update, context)
        elif text in ['регистрации', 'реєстраціі']:
            current_registrations(update, context)
        elif text in ['расписание', 'розклад']:
            handle_schedule(update, context)
        elif text in ['изменить регион', 'змінити регіон']:
            change_region(update, context)
        elif text in ['изменить язык', 'змінити мову']:
            change_language(update, context)
        elif text in ['текущие регистрации', 'поточні реєстрації']:
            current_registrations(update, context)
        elif text in ["главное меню", "головне меню"]:
            send_main_menu(update, context)
        else:
            if context.user_data.get('qna'):
                question_text_handler(update, context)


def error_callback(update, context):
    try:
        raise context.error
    except NetworkError as e:
        print(f"NetworkError occurred: {e}. Retrying...")
        sleep(1)  # Wait for 1 second before retrying


# And in your main function:
def main() -> None:
    updater = Updater("6009306710:AAH0Oy97tOg9D6i3fQZxGdHoU54caxwBM-I")
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('Добавить событие'), add_event)],
        states={
            NAME: [MessageHandler(Filters.text & ~Filters.command, handle_name)],
            DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, handle_description)],
            LOCATION: [MessageHandler(Filters.text & ~Filters.command, handle_location)],
            DATE: [MessageHandler(Filters.text & ~Filters.command, handle_date)],
            PHOTO: [MessageHandler(Filters.photo, handle_photo)],
            PRICELINK: [MessageHandler(Filters.text & ~Filters.command, handle_payment)],
            PRICE: [MessageHandler(Filters.text & ~Filters.command, handle_price)],
            REGION: [
                CallbackQueryHandler(handle_region, pattern='^(region1|region2)$'),
                CallbackQueryHandler(handle_save, pattern='^save$'),
                CallbackQueryHandler(handle_cancel, pattern='^cancel$')
            ]

        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    updater.dispatcher.add_handler(conv_handler)
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_region_selection, pattern='^region_'))
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_delete, pattern='^delete_.*$'))
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(button_lang, pattern='^(russian|ukranian)$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(button_region, pattern='^(region1|region2)$'))

    # updater.dispatcher.add_handler(CallbackQueryHandler(button_change_region, pattern='^(regionchange1|regionchange2'
    #                                                                                   '|cancel)$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(button_change_language, pattern='^(russianchange'
                                                                                        '|ukrainianchange)$'))
    updater.dispatcher.add_handler(CommandHandler('schedule', handle_schedule))
    updater.dispatcher.add_handler(
        CallbackQueryHandler(handle_event_navigation, pattern='^(previous_event|next_event)$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_registration, pattern='^register$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_approve, pattern='^approve$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_notapprove, pattern='^notapprove$'))
    updater.dispatcher.add_handler(MessageHandler(Filters.contact, phone_number_handler))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, text_handler))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), question_text_handler))
    updater.dispatcher.add_error_handler(error_callback)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
