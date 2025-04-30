import json
import os
import random
from pathlib import Path


def save_user(user_id: int, user_nick: int, role: str = 'user'):
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
            data = {}

    data[user_id] = {
        'user_nick': user_nick,
        'role': role
    }
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except IOError as e:
        raise IOError(f"Ошибка при записи данных в файл '{file_path}': {e}")


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

    data = {}
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка при чтении файла: {e}")
            data = {}
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

    data = {}
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка при чтении файла: {e}")
            data = {}

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

    data = {}
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
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

    data = {}
    if file.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка при чтении файла: {e}")
            data = {}

    index = 0
    for num, i in enumerate(data['dialogs']):
        if user_id in i:
            index = num
    del data['dialogs'][index]

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except IOError as e:
        raise IOError(f"Ошибка при записи данных в файл '{file_path}': {e}")
