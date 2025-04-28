"""
Модуль для работы с Yandex Cloud SDK
"""

from ..utils.sdk_init import initialize_sdk
from ..utils.config import load_config

def create_thread(sdk):
    """Создание диалога"""
    return sdk.threads.create(ttl_days=1, expiration_policy="static")

def create_assistant(sdk, thread):
    """Создание ассистента"""
    config = load_config()
    model = sdk.models.completions("yandexgpt", model_version="rc")
    
    # Получаем ID индекса
    index_id = config["search_index"]["id"]
    if index_id:
        # Получаем индекс
        index = sdk.search_indexes.get(index_id)
        print(f"\nАссистент использует индекс {index_id}")
        
        # Создаем поисковый инструмент
        search_tool = sdk.tools.search_index(index)
        
        # Создаем ассистента с поисковым инструментом
        assistant = sdk.assistants.create(
            model, 
            ttl_days=1, 
            expiration_policy="since_last_active",
            tools=[search_tool]
        )
        
        instruction = """
        Ты - опытный сомелье, в задачу которого входит отвечать на вопросы пользователя про вина
        и рекомендовать лучшие вина к еде. Посмотри на всю имеющуюся в твоем распоряжении информацию
        и выдай одну или несколько лучших рекомендаций. Если что-то непонятно, то лучше уточни информацию
        у пользователя.
        """
        
        assistant.update(instruction=instruction)
        print("Ассистент создан с поисковым инструментом!")
    else:
        # Создаем ассистента без индекса
        assistant = sdk.assistants.create(
            model, 
            ttl_days=1, 
            expiration_policy="since_last_active"
        )
        print("\nАссистент создан без индекса")
        
        assistant.update(
            instruction="""Ты - опытный сомелье, задача которого - консультировать пользователя в
            вопросах выбора вина. Используй загруженные файлы для ответов.
            
            Всегда форматируй ответы в Markdown:
            - Используй **жирный текст** для названий регионов и важных терминов
            - Используй списки с цифрами (1., 2., 3.) или маркерами (-) для перечислений
            - Используй курсив для названий сортов винограда
            - Добавляй краткое описание каждого вина
            - Группируй вина по регионам, если их несколько"""
        )
    
    return assistant 