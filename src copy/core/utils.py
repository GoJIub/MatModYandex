"""
Модуль с общими утилитами
"""

import json
import os
import logging
from typing import List, Optional, Dict
import random
from datetime import datetime

# Инициализация логгера
logger = logging.getLogger(__name__)

# Пути к файлам данных
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'telegram_bot_data')
users_file = os.path.join(data_dir, 'users.json')
callstack_file = os.path.join(data_dir, 'callstack.json')

def save_user(user_id: int, user_nick: str, role: str = 'user') -> bool:
    """Сохранение информации о пользователе"""
    try:
        # Читаем существующие данные
        if os.path.exists(users_file):
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        else:
            users = {}
            
        # Обновляем или добавляем пользователя
        users[str(user_id)] = {
            'nick': user_nick,
            'role': role
        }
        
        # Сохраняем обновленные данные
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=4)
            
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя: {e}")
        return False

def update_user_role(user_id: int, new_role: str) -> bool:
    """Изменение роли пользователя"""
    try:
        if not os.path.exists(users_file):
            return False

        with open(users_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {}

        if str(user_id) in data:
            data[str(user_id)]['role'] = new_role
        else:
            data[str(user_id)] = {
                'nick': str(user_id),
                'role': new_role
            }

        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении роли пользователя: {e}")
        return False

def get_all_admin_ids() -> List[int]:
    """Получение списка ID администраторов"""
    try:
        if not os.path.exists(users_file):
            return []

        with open(users_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return []

        admin_ids = [int(user_id) for user_id, user_data in data.items() 
                    if user_data.get('role') == 'admin']
        logger.info(f"Найдены админы: {admin_ids}")
        return admin_ids
    except Exception as e:
        logger.error(f"Ошибка при получении списка админов: {e}")
        return []

def stay_in_quire(user_id: int) -> Optional[int]:
    """Добавление пользователя в очередь"""
    try:
        if not os.path.exists(callstack_file):
            os.makedirs(os.path.dirname(callstack_file), exist_ok=True)
            data = {'queue': [], 'dialogs': []}
            with open(callstack_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        with open(callstack_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {'queue': [], 'dialogs': []}

        if 'queue' not in data:
            data['queue'] = []

        if user_id in data['queue']:
            return data['queue'].index(user_id) + 1

        data['queue'].append(user_id)
        logger.info(f"Добавлен пользователь {user_id} в очередь. Текущая очередь: {data['queue']}")

        with open(callstack_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return len(data['queue'])
    except Exception as e:
        logger.error(f"Ошибка при добавлении в очередь: {e}")
        return None

def create_dialog(admin_id: int, user_id: Optional[int] = None) -> Optional[tuple]:
    """Создание диалога между пользователем и администратором"""
    try:
        if not os.path.exists(callstack_file):
            os.makedirs(os.path.dirname(callstack_file), exist_ok=True)
            data = {'queue': [], 'dialogs': []}
            with open(callstack_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        with open(callstack_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {'queue': [], 'dialogs': []}

        if 'dialogs' not in data:
            data['dialogs'] = []

        # Проверяем, не занят ли администратор
        for dialog in data['dialogs']:
            if dialog.get('admin_id') == admin_id:
                logger.warning(f"Администратор {admin_id} уже в диалоге")
                return None

        # Если user_id не указан, берем первого из очереди
        if user_id is None:
            if not data.get('queue'):
                logger.warning("Очередь пуста")
                return None
            user_id = data['queue'].pop(0)
        elif user_id in data.get('queue', []):
            data['queue'].remove(user_id)

        # Проверяем, не занят ли пользователь
        for dialog in data['dialogs']:
            if dialog.get('user_id') == user_id:
                logger.warning(f"Пользователь {user_id} уже в диалоге")
                return None

        # Создаем новый диалог
        new_dialog = {
            'user_id': user_id,
            'admin_id': admin_id,
            'start_time': datetime.now().isoformat()
        }
        data['dialogs'].append(new_dialog)

        with open(callstack_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        logger.info(f"Создан диалог между пользователем {user_id} и администратором {admin_id}")
        return (user_id, admin_id)
    except Exception as e:
        logger.error(f"Ошибка при создании диалога: {e}")
        return None

def get_visavi(user_id: int) -> Optional[int]:
    """Получение ID собеседника"""
    try:
        if not os.path.exists(callstack_file):
            return None

        with open(callstack_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return None

        for dialog in data.get('dialogs', []):
            if dialog.get('user_id') == user_id:
                return dialog.get('admin_id')
            if dialog.get('admin_id') == user_id:
                return dialog.get('user_id')

        return None
    except Exception as e:
        logger.error(f"Ошибка при получении собеседника: {e}")
        return None

def stop_dialog(user_id: int) -> bool:
    """Завершение диалога"""
    try:
        if not os.path.exists(callstack_file):
            return False

        with open(callstack_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return False

        dialog_found = False
        for i, dialog in enumerate(data.get('dialogs', [])):
            if dialog.get('user_id') == user_id or dialog.get('admin_id') == user_id:
                del data['dialogs'][i]
                dialog_found = True
                break

        if dialog_found:
            with open(callstack_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.info(f"Диалог пользователя {user_id} завершен")
            return True

        return False
    except Exception as e:
        logger.error(f"Ошибка при завершении диалога: {e}")
        return False

def get_random_music() -> Optional[str]:
    """Получение случайного музыкального файла"""
    music_folder = os.path.join(data_dir, 'music')
    if not os.path.exists(music_folder):
        os.makedirs(music_folder)
        return None

    music_files = [f for f in os.listdir(music_folder) if f.endswith(('.mp3', '.ogg', '.wav'))]
    if not music_files:
        return None

    return os.path.join(music_folder, random.choice(music_files)) 