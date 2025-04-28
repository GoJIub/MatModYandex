import os
from dotenv import load_dotenv
from yandex_cloud_ml_sdk import YCloudML

# Загрузка переменных окружения из .env файла
load_dotenv()

def initialize_sdk():
    folder_id = os.environ.get("folder_id")
    api_key = os.environ.get("api_key")
    
    if not folder_id or not api_key:
        raise ValueError("Не найдены необходимые переменные окружения")
        
    return YCloudML(folder_id=folder_id, auth=api_key)

def create_thread(sdk):
    return sdk.threads.create(ttl_days=1, expiration_policy="static")

def create_assistant(sdk, thread):
    model = sdk.models.completions("yandexgpt", model_version="rc")
    assistant = sdk.assistants.create(
        model, ttl_days=1, expiration_policy="since_last_active"
    )
    
    assistant.update(
        instruction="""Ты - опытный сомелье, задача которого - консультировать пользователя в
        вопросах выбора вина."""
    )
    
    return assistant
