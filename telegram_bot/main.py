import telebot
from telebot import types
import os
from dotenv import load_dotenv
import logging
import time
import json
import signal
import sys
from telegram_bot.functions import (save_user, update_user_role, get_all_admin_ids, stop_dialog,
                       stay_in_quire, create_dialog, get_visavi, get_random_music)
from src.core.assistant import AdmissionsAssistant

# Загрузка переменных окружения
start_time = time.time()
load_dotenv()
logger = logging.getLogger(__name__)
logger.info(f"Загрузка переменных окружения: {time.time() - start_time:.2f} сек")

# Инициализация логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Создание директории для данных бота
data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'telegram_bot_data')
os.makedirs(data_dir, exist_ok=True)

# Создание файла users.json, если его нет
users_file = os.path.join(data_dir, 'users.json')
if not os.path.exists(users_file):
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=4)
    logger.info("Создан файл users.json")

# Получение конфигурации из переменных окружения
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(",") if id]

if not BOT_TOKEN:
    logger.error("Не указан TELEGRAM_BOT_TOKEN в .env файле!")
    exit(1)

# Инициализация бота и ассистента
logger.info("Инициализация бота...")
bot = telebot.TeleBot(BOT_TOKEN)
assistants = {}  # Словарь для хранения ассистентов для каждого пользователя
calling_admin = dict()
logger.info(f"Инициализация завершена: {time.time() - start_time:.2f} сек")

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info("Получен сигнал завершения работы. Останавливаем бота...")
    for assistant in assistants.values():
        try:
            assistant.cleanup()
        except Exception as e:
            logger.error(f"Ошибка при очистке ассистента: {e}")
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_or_create_assistant(user_id):
    """Получение или создание ассистента для пользователя"""
    if user_id not in assistants:
        assistants[user_id] = AdmissionsAssistant()
        assistants[user_id].start()
    return assistants[user_id]

@bot.message_handler(commands=['start'])
def start_message(message):
    text_first = '''Привет! Я бот приемной комиссии МАИ.
Задавай свои вопросы, я с радостью на них отвечу.
Если ты админ, пришли admin.'''

    save_user(message.chat.id, user_nick=message.chat.username, role='user')
    
    # Инициализируем ассистента для пользователя
    get_or_create_assistant(message.chat.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_admin = types.KeyboardButton("Связаться с админом")
    markup.add(button_admin)
    bot.send_message(message.chat.id, text_first, reply_markup=markup)

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

        elif message.text == '12345':
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

        elif message.text == "Связаться с админом":
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

        elif message.text == 'Узнать положение в очереди':
            place = stay_in_quire(message.chat.id)
            if place is True:
                text = 'Вы следующий в очереди!'
            elif place:
                text = f'Вы в очереди на {place} месте.'
            else:
                text = 'Вы не в очереди.'

            bot.send_message(message.chat.id, text)
            
        else:
            # Обработка сообщений через ассистента
            try:
                assistant = get_or_create_assistant(message.chat.id)
                response = assistant.ask(message.text)
                bot.send_message(message.chat.id, response)
            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения: {e}")
                bot.send_message(message.chat.id, "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")

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

if __name__ == "__main__":
    logger.info("Запуск бота...")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        # Очистка ресурсов при завершении
        for assistant in assistants.values():
            try:
                assistant.cleanup()
            except Exception as e:
                logger.error(f"Ошибка при очистке ассистента: {e}")