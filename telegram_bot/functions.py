import json
import os
import random
from pathlib import Path
from src.core.assistant import AdmissionsAssistant
from typing import List, Dict, Optional

# Путь к файлу с данными пользователей
data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'telegram_bot_data')
users_file = os.path.join(data_dir, 'users.json')

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
        print(f"Ошибка при сохранении пользователя: {e}")
        return False


def update_user_role(user_id: int, new_role: str):
    """
    Изменяет роль пользователя по его уникальному идентификатору.
    Аргументы:
        user_id: уникальный идентификатор пользователя
        new_role: новая роль пользователя
    Возвращает:
        bool: True, если роль была успешно изменена, иначе False
    """
    file_path = '../telegram_bot_data/users.json'
    file = Path(file_path)

    # Загружаем существующие данные или создаем пустой словарь
    data = {}
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except (json.JSONDecodeError, IOError) as e:
            return False

    if str(user_id) in data:
        data[str(user_id)]['role'] = new_role
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except IOError as e:
            raise IOError(f"Ошибка при изменении данных в файл '{file_path}': {e}")
    else:
        return False


def get_all_admin_ids():
    """
    Возвращает список всех ID пользователей с ролью 'admin'.
    Возвращает:
        list: список всех ID администраторов
    """
    file_path = '../telegram_bot_data/users.json'
    file = Path(file_path)

    data = {}
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка при чтении файла: {e}")
            return []
    admin_ids = [user_id for user_id, user_data in data.items() if user_data.get('role') == 'admin']
    return admin_ids


def stay_in_quire(user_id):
    file_path = '../telegram_bot_data/callstack.json'
    file = Path(file_path)

    data = {'queue': [], 'dialogs': []}  # Initialize with empty lists
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {'queue': [], 'dialogs': []}
                # Ensure required keys exist
                if 'queue' not in data:
                    data['queue'] = []
                if 'dialogs' not in data:
                    data['dialogs'] = []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка при чтении файла: {e}")
            
    if any(user_id == i for i in data['queue']):
        return data['queue'].index(user_id) + 1
    data['queue'].append(user_id)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except IOError as e:
        raise IOError(f"Ошибка при записи данных в файл '{file_path}': {e}")


def create_dialog(admins_id):
    file_path = '../telegram_bot_data/callstack.json'
    file = Path(file_path)

    data = {'queue': [], 'dialogs': []}  # Initialize with empty lists
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {'queue': [], 'dialogs': []}
                # Ensure required keys exist
                if 'queue' not in data:
                    data['queue'] = []
                if 'dialogs' not in data:
                    data['dialogs'] = []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка при чтении файла: {e}")

    if not data['queue']:  # Check if queue is empty
        return False

    dialog = [data['queue'][0], admins_id]
    data['dialogs'].append(dialog)
    del data['queue'][0]

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except IOError as e:
        raise IOError(f"Ошибка при записи данных в файл '{file_path}': {e}")


def get_visavi(user_id):
    file_path = '../telegram_bot_data/callstack.json'
    file = Path(file_path)

    data = {'queue': [], 'dialogs': []}  # Initialize with empty lists
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {'queue': [], 'dialogs': []}
                # Ensure required keys exist
                if 'queue' not in data:
                    data['queue'] = []
                if 'dialogs' not in data:
                    data['dialogs'] = []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка при чтении файла: {e}")
            return False
            
    for dialog in data['dialogs']:
        if dialog[0] == user_id:
            return dialog[1]
        if dialog[1] == user_id:
            return dialog[0]
    return False


def get_random_music():
    music_folder = '../telegram_bot_data/music'
    if not os.path.exists(music_folder):
        os.makedirs(music_folder)
        return None

    music_files = [f for f in os.listdir(music_folder) if f.endswith(('.mp3', '.ogg', '.wav'))]
    if not music_files:
        return None

    return os.path.join(music_folder, random.choice(music_files))


def stop_dialog(user_id):
    file_path = '../telegram_bot_data/callstack.json'
    file = Path(file_path)

    data = {'queue': [], 'dialogs': []}  # Initialize with empty lists
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {'queue': [], 'dialogs': []}
                # Ensure required keys exist
                if 'queue' not in data:
                    data['queue'] = []
                if 'dialogs' not in data:
                    data['dialogs'] = []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка при чтении файла: {e}")
            return False

    # Find and remove the dialog containing user_id
    for i, dialog in enumerate(data['dialogs']):
        if user_id in dialog:
            del data['dialogs'][i]
            break

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except IOError as e:
        raise IOError(f"Ошибка при записи данных в файл '{file_path}': {e}")


def get_user_context(user_id: int) -> Dict:
    """Получение контекста пользователя"""
    try:
        if not os.path.exists(users_file):
            return {}
            
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
            
        if str(user_id) not in users:
            return {}
            
        return users[str(user_id)].get('assistant_context', {})
    except Exception as e:
        print(f"Ошибка при получении контекста пользователя: {e}")
        return {}


def update_user_context(user_id: int, context: Dict) -> bool:
    """Обновление контекста пользователя"""
    try:
        if not os.path.exists(users_file):
            return False
            
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
            
        if str(user_id) not in users:
            return False
            
        users[str(user_id)]['assistant_context'] = context
        
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=4)
            
        return True
    except Exception as e:
        print(f"Ошибка при обновлении контекста пользователя: {e}")
        return False


def get_user(user_id: int) -> Optional[Dict]:
    """Получение информации о пользователе"""
    try:
        if not os.path.exists(users_file):
            return None
            
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
            
        return users.get(str(user_id))
    except Exception as e:
        print(f"Ошибка при получении данных пользователя: {e}")
        return None


def save_user_context(user_id: int, context: Dict) -> bool:
    """Сохранение контекста пользователя"""
    try:
        users = {}
        if os.path.exists(users_file):
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
                
        if str(user_id) not in users:
            users[str(user_id)] = {}
            
        users[str(user_id)]['assistant_context'] = context
        
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=4)
            
        return True
    except Exception as e:
        print(f"Ошибка при сохранении контекста пользователя: {e}")
        return False
