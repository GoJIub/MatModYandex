"""
Модуль конфигурации
"""

import os
from pathlib import Path
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Загрузка конфигурации"""
    return {
        "data_dir": os.getenv("DATA_DIR", "data"),
        "model": {
            "name": "yandexgpt",
            "version": "rc"
        },
        "assistant": {
            "ttl_days": 1,
            "expiration_policy": "since_last_active"
        },
        "search_index": {
            "id": os.getenv("SEARCH_INDEX_ID", "")
        }
    }

def save_search_index_id(index_id: str):
    """Сохранение ID индекса в конфигурации"""
    env_path = Path(".env")
    
    # Читаем существующий файл
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Ищем строку с SEARCH_INDEX_ID
    found = False
    for i, line in enumerate(lines):
        if line.startswith("SEARCH_INDEX_ID="):
            lines[i] = f"SEARCH_INDEX_ID={index_id}\n"
            found = True
            break
    
    # Если строка не найдена, добавляем новую
    if not found:
        lines.append(f"SEARCH_INDEX_ID={index_id}\n")
    
    # Записываем обновленный файл
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines) 