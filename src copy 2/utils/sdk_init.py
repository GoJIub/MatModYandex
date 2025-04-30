"""
Модуль для инициализации SDK
"""

import os
from dotenv import load_dotenv
from yandex_cloud_ml_sdk import YCloudML

def initialize_sdk():
    """Инициализация SDK Yandex Cloud"""
    load_dotenv()
    
    folder_id = os.environ.get("folder_id")
    api_key = os.environ.get("api_key")
    
    if not folder_id or not api_key:
        raise ValueError("Не найдены необходимые переменные окружения")
        
    return YCloudML(folder_id=folder_id, auth=api_key) 