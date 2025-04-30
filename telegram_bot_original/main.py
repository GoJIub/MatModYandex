import telebot
from telebot import types
from config import Config
import logging
from functions import (save_user, update_user_role, get_all_admin_ids, stop_dialog,
                       stay_in_quire, create_dialog, get_visavi, get_random_music)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
config = Config(_env_file='../.env')
ADMIN_IDS = [int(id) for id in config.admin_ids.split(",") if id]
if not config.bot_token:
    logger.error("Не указан TELEGRAM_BOT_TOKEN в .env файле!")
    exit(1)

bot = telebot.TeleBot(config.bot_token)
calling_admin = dict()


@bot.message_handler(commands=['start'])
def start_message(message):
    text_first = '''Привет! Я бот приемной комиссии МАИ.
Задавай свои вопросы, я с радостью на них отвечу.
Если ты админ, пришли admin.'''

    save_user(message.chat.id, user_nick=message.chat.username,role='user')

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_admin = types.KeyboardButton("Связаться с админом")
    markup.add(button_admin)
    bot.send_message(message.chat.id, text_first, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'queue_position')
def handle_queue_position(call):
    place = stay_in_quire(call.message.chat.id)
    if place is True:  # Если очередь пуста или пользователь первый
        text = 'Вы следующий в очереди!'
    elif place:  # Если есть конкретная позиция
        text = f'Вы в очереди на {place} месте.'
    else:  # Если пользователя нет в очереди
        text = 'Вы не в очереди.'

    bot.answer_callback_query(call.id, text)


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def handle_confirmation(call):
    user_id = call.data.split('_')[1]

    admins = get_all_admin_ids()
    for admin_id in admins:
        if admin_id in calling_admin:
            try:
                bot.delete_message(admin_id, calling_admin[admin_id])
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")
            finally:
                calling_admin.pop(admin_id, None)

    create_dialog(call.message.chat.id)

        # Отправляем сообщение админу
    text = '''Спасибо за вашу инициативность.
    Перенаправляю на чат с пользователем.'''
    bot.send_message(call.message.chat.id, text)

        # Отправляем сообщение пользователю
    bot.send_message(user_id, 'Администратор принял ваш запрос. Можете общаться.')


@bot.message_handler(content_types='text')
def message_reply(message):
    visavi = get_visavi(message.chat.id)
    if visavi:
        if message.text == 'Закончить беседу':
            stop_dialog(message.chat.id)
            bot.send_message(message.chat.id, 'Спасибо за беседу, контакт разорван.')
            bot.send_message(visavi, 'Спасибо за беседу, контакт разорван.')
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            button_stop = types.KeyboardButton("Закончить беседу")
            markup.add(button_stop)
            bot.send_message(visavi, message.text, reply_markup=markup)
    else:

        if message.text == 'admin':
            text = 'Введи код.'
            markup = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, text, reply_markup=markup)

        if message.text == '12345':
            if update_user_role(message.chat.id, 'admin'):
                text = 'Вы успешно зарегистрированы как админ'
                markup = types.ReplyKeyboardRemove()
                bot.send_message(message.chat.id, text, reply_markup=markup)
            else:
                text = 'Пароль верен, попробуйте позже или свяжитесь с админом'
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                button_admin = types.KeyboardButton("Связаться с админом")
                markup.add(button_admin)
                bot.send_message(message.chat.id, text, reply_markup=markup)

        if message.text == "Связаться с админом":
            admins = get_all_admin_ids()
            if len(admins) == 0:
                markup = types.ReplyKeyboardRemove()
                bot.send_message(message.chat.id, 'Технические шоколадки, попробуйте позже',
                                          reply_markup=markup)
            else:
                place = stay_in_quire(message.chat.id)
                if place and place is not True:
                    text = f'Вы уже в очереди на {place} месте.'
                    bot.send_message(message.chat.id, text)
                else:
                    text = 'Заявка отправлена администраторам, пожалуйста ожидайте. \n\nА пока можете послушать музыку:'
                    markup = types.InlineKeyboardMarkup()
                    button_text = 'Узнать положение в очереди'
                    button_agree = types.InlineKeyboardButton(button_text, callback_data='queue_position')
                    markup.add(button_agree)
                    bot.send_message(message.chat.id, text, reply_markup=markup)

                    music_path = get_random_music()
                    if music_path:
                        with open(music_path, 'rb') as audio_file:
                            bot.send_audio(message.chat.id, audio_file)
                    else:
                        bot.send_message(message.chat.id, "К сожалению, музыкальные треки временно недоступны")

                    for id in admins:
                        text = 'С вами хотят связаться.'
                        markup = types.InlineKeyboardMarkup()
                        button_agree = types.InlineKeyboardButton(
                            '✅Подтвердить',
                            callback_data=f'confirm_{message.chat.id}'
                        )
                        markup.add(button_agree)
                        mes_id = bot.send_message(id, text, reply_markup=markup)
                        calling_admin[id] = mes_id.message_id

        if message.text == 'Узнать положение в очереди':
            place = stay_in_quire(message.chat.id)
            if place is True:
                text = 'Вы следующий в очереди!'
            elif place:
                text = f'Вы в очереди на {place} месте.'
            else:
                text = 'Вы не в очереди.'

            bot.send_message(message.chat.id, text)


bot.infinity_polling()