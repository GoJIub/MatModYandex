import telebot
from telebot import types
import os
from dotenv import load_dotenv
import logging
import time
import json
import signal
import sys
from src.core.utils import (
    save_user, update_user_role, get_all_admin_ids, stop_dialog,
    stay_in_quire, create_dialog, get_visavi, get_random_music
)
from src.core.assistant import AdmissionsAssistant
from src.core.sdk import set_bot, create_assistant

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

# Создание директории для логов
logs_dir = os.path.join(data_dir, 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Создание файла users.json, если его нет
users_file = os.path.join(data_dir, 'users.json')
if not os.path.exists(users_file):
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=4)
    logger.info("Создан файл users.json")

# Создание файлового логгера
file_handler = logging.FileHandler(
    os.path.join(logs_dir, f'bot_{time.strftime("%Y%m%d")}.log'),
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

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
chat_history = {}  # Словарь для хранения истории чатов
logger.info(f"Инициализация завершена: {time.time() - start_time:.2f} сек")

# Устанавливаем экземпляр бота для класса Handover
set_bot(bot)

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

def cleanup_assistant(user_id):
    """Очистка ресурсов ассистента"""
    if user_id in assistants:
        try:
            assistants[user_id].cleanup()
            del assistants[user_id]
            logger.info(f"Assistant cleaned up for user {user_id}")
        except Exception as e:
            logger.error(f"Error cleaning up assistant for user {user_id}: {e}")

@bot.message_handler(commands=['start'])
def start_message(message):
    text_first = '''Привет! Я бот приемной комиссии МАИ.
Задавай свои вопросы, я с радостью на них отвечу.'''

    save_user(message.chat.id, user_nick=message.chat.username, role='user')
    
    # Инициализируем ассистента для пользователя
    get_or_create_assistant(message.chat.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_admin = types.KeyboardButton("Связаться с админом")
    markup.add(button_admin)
    bot.send_message(message.chat.id, text_first, reply_markup=markup)

@bot.message_handler(commands=['stop'])
def stop_command(message):
    """Обработчик команды /stop для завершения диалога"""
    logger.info(f"User {message.chat.id} ({message.chat.username}) requested to stop dialog")
    if stop_dialog(message.chat.id):
        bot.send_message(message.chat.id, "Диалог завершен. Спасибо за обращение!")
    else:
        bot.send_message(message.chat.id, "Вы не находитесь в активном диалоге.")

@bot.message_handler(content_types='text')
def message_reply(message):
    # Логируем входящее сообщение
    logger.info(f"User {message.chat.id} ({message.chat.username}): {message.text}")
    
    # Проверяем, находится ли пользователь в диалоге с админом
    visavi = get_visavi(message.chat.id)
    if visavi:
        # Если пользователь в диалоге, перенаправляем сообщение собеседнику
        try:
            # Форматируем сообщение для админа/пользователя
            if message.chat.username:
                forward_text = f"[{message.chat.username}]: {message.text}"
            else:
                forward_text = f"[User {message.chat.id}]: {message.text}"
            
            # Отправляем сообщение собеседнику
            bot.send_message(visavi, forward_text)
            return
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            bot.send_message(message.chat.id, "Ошибка при отправке сообщения. Возможно, диалог был завершен.")
            stop_dialog(message.chat.id)
            return
    
    # Если пользователь не в диалоге, обрабатываем команды и взаимодействие с ботом
    if message.text.lower() in ['завершить', 'закончить', 'стоп', 'stop', 'end']:
        stop_dialog(message.chat.id)
        bot.send_message(message.chat.id, "Диалог завершен. Спасибо за обращение!")
        return
    
    # Проверяем, является ли сообщение запросом на авторизацию админа
    if message.text.lower() == 'admin':
        logger.info(f"Admin authentication requested by {message.chat.id}")
        bot.send_message(message.chat.id, "Введите пароль для авторизации:")
        return
    
    # Проверяем, является ли сообщение паролем админа
    if message.text.lower() == 'kantorka':
        if update_user_role(message.chat.id, 'admin'):
            logger.info(f"User {message.chat.id} successfully registered as admin")
            bot.send_message(message.chat.id, "Вы успешно авторизованы как администратор!")
        else:
            logger.warning(f"Failed to register admin for user {message.chat.id}")
            bot.send_message(message.chat.id, "Ошибка авторизации. Попробуйте позже.")
        return
    
    # Обработка обычных сообщений через ассистента
    try:
        assistant = get_or_create_assistant(message.chat.id)
        response = assistant.ask(message.text)
        
        # Сохраняем сообщение и ответ в историю
        if message.chat.id not in chat_history:
            chat_history[message.chat.id] = []
        chat_history[message.chat.id].append({
            'user': message.text,
            'assistant': response if isinstance(response, str) else "Вызов функции"
        })
        
        if isinstance(response, dict) and 'function_call' in response:
            function_call = response['function_call']
            if function_call['name'] == 'handover_to_operator':
                # Получаем список всех админов
                admins = get_all_admin_ids()
                logger.info(f"Найдены админы: {admins}")
                
                if not admins:
                    bot.send_message(message.chat.id, "К сожалению, сейчас нет доступных операторов. Попробуйте позже.")
                    return
                
                # Добавляем пользователя в очередь
                queue_position = stay_in_quire(message.chat.id)
                if queue_position is None:
                    bot.send_message(message.chat.id, "Произошла ошибка при добавлении в очередь. Пожалуйста, попробуйте позже.")
                    return
                
                # Отправляем сообщение всем админам
                for admin_id in admins:
                    try:
                        markup = types.InlineKeyboardMarkup()
                        button_agree = types.InlineKeyboardButton(
                            '✅Подтвердить',
                            callback_data=f'confirm_{message.chat.id}'
                        )
                        markup.add(button_agree)
                        text = f'С вами хочет связаться пользователь {message.chat.username or message.chat.id}.'
                        mes_id = bot.send_message(admin_id, text, reply_markup=markup)
                        calling_admin[admin_id] = mes_id.message_id
                        logger.info(f"Отправлено сообщение админу {admin_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке сообщения админу {admin_id}: {e}")
                
                # Отправляем пользователю сообщение о его позиции в очереди
                text = 'Заявка отправлена администраторам, пожалуйста ожидайте. \n\nА пока можете послушать музыку:'
                markup = types.InlineKeyboardMarkup()
                button_text = 'Узнать положение в очереди'
                button_agree = types.InlineKeyboardButton(button_text, callback_data='queue_position')
                markup.add(button_agree)
                bot.send_message(message.chat.id, text, reply_markup=markup)
                
                # Воспроизводим музыку во время ожидания
                music_path = get_random_music()
                if music_path:
                    with open(music_path, 'rb') as audio_file:
                        bot.send_audio(message.chat.id, audio_file)
                else:
                    bot.send_message(message.chat.id, "К сожалению, музыкальные треки временно недоступны")
                    logger.warning("No music files available")
                
                # Очищаем ресурсы ассистента после передачи оператору
                cleanup_assistant(message.chat.id)
                return
                
        elif response and response.strip():
            logger.info(f"Assistant response to user {message.chat.id}: {response}")
            bot.send_message(message.chat.id, response)
        else:
            logger.info(f"Empty response from assistant for user {message.chat.id}, sent default message")
            bot.send_message(message.chat.id, "Извините, я не смог обработать ваш запрос. Попробуйте переформулировать вопрос.")
            
    except Exception as e:
        logger.error(f"Error processing message from user {message.chat.id}: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте позже.")

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
    user_id = int(call.data.split('_')[1])
    admin_id = call.message.chat.id
    
    # Удаляем сообщения с кнопками у всех админов
    admins = get_all_admin_ids()
    for admin in admins:
        if admin in calling_admin:
            try:
                bot.delete_message(admin, calling_admin[admin])
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
            finally:
                calling_admin.pop(admin, None)
    
    # Создаем диалог
    result = create_dialog(admin_id, user_id)
    if result:
        # Отправляем историю чата админу
        if user_id in chat_history:
            history_text = "История чата с пользователем:\n\n"
            for msg in chat_history[user_id]:
                history_text += f"Пользователь: {msg['user']}\n"
                history_text += f"Ассистент: {msg['assistant']}\n\n"
            bot.send_message(admin_id, history_text)
            # Очищаем историю после отправки
            del chat_history[user_id]
        
        # Очищаем ассистента пользователя
        cleanup_assistant(user_id)
        
        # Отправляем сообщение админу
        bot.send_message(admin_id, 
            f"Вы начали диалог с пользователем {user_id}.\n"
            "Все сообщения будут пересылаться между вами.\n"
            "Для завершения диалога отправьте команду /stop")
        
        # Отправляем сообщение пользователю
        bot.send_message(user_id, 
            "Администратор принял ваш запрос. Теперь вы можете общаться напрямую.\n"
            "Для завершения диалога отправьте команду /stop")
    else:
        bot.send_message(admin_id, "Не удалось создать диалог. Возможно, пользователь уже общается с другим администратором.")
        bot.send_message(user_id, "К сожалению, не удалось установить соединение с администратором. Попробуйте позже.")

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