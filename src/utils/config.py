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
    with open(".env", "a") as f:
        f.write(f"\nSEARCH_INDEX_ID={index_id}") 