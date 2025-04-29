"""
Модуль для работы с Yandex Cloud SDK
"""

from ..utils.sdk_init import initialize_sdk
from ..utils.config import load_config
from pydantic import BaseModel, Field
from typing import List, Optional
import json
import os

class SearchAdmissionInfo(BaseModel):
    """Поиск информации о поступлении"""
    query: str = Field(description="Поисковый запрос")
    year: Optional[int] = Field(description="Год поступления", default=None)
    program: Optional[str] = Field(description="Программа обучения", default=None)

class Handover(BaseModel):
    """Эта функция позволяет передать диалог человеку-оператору приёмной комиссии"""
    reason: str = Field(
        description="Причина для вызова оператора", 
        default="не указана"
    )

    def process(self, thread):
        return f"Я передам ваш вопрос оператору приёмной комиссии. ID диалога: {thread.id}, причина: {self.reason}"

def create_thread(sdk):
    """Создание диалога"""
    return sdk.threads.create(ttl_days=1, expiration_policy="static")

def create_assistant(sdk, thread):
    """Создание ассистента"""
    config = load_config()
    model = sdk.models.completions("yandexgpt", model_version="rc")
    
    # Загружаем ID индексов
    indices = {}
    if os.path.exists("indices.json"):
        with open("indices.json", "r") as f:
            indices = json.load(f)
    
    if indices:
        print("\nАссистент использует индексы:")
        search_tools = []
        for year, index_id in indices.items():
            print(f"- {year}: {index_id}")
            index = sdk.search_indexes.get(index_id)
            search_tools.append(sdk.tools.search_index(index))
        
        # Создаем инструменты для Function Calling
        admission_search_tool = sdk.tools.function(SearchAdmissionInfo)
        handover_tool = sdk.tools.function(Handover)
        
        # Создаем ассистента с инструментами
        assistant = sdk.assistants.create(
            model, 
            ttl_days=1, 
            expiration_policy="since_last_active",
            tools=search_tools + [admission_search_tool, handover_tool]
        )
        
        instruction = """
        Ты - опытный работник приёмной комиссии Московского авиационного института (МАИ), задача которого - 
        консультировать абитуриентов по всем вопросам поступления в университет. В твоём распоряжении:
        
        1. Полная информация о:
           - Программах обучения и специальностях
           - Вступительных испытаниях и экзаменах
           - Проходных баллах прошлых лет
           - Особенностях приёмной кампании текущего года
           - Правилах подачи документов
           - Сроках и этапах поступления
        
        2. История консультаций приёмной комиссии за предыдущие годы
        
        Твои основные задачи:
        - Давать точные и актуальные ответы на вопросы абитуриентов
        - Предлагать оптимальные стратегии поступления с учётом индивидуальной ситуации
        - При необходимости запрашивать дополнительную информацию для более точной консультации
        - Вести диалог в вежливом и профессиональном тоне
        
        Для поиска конкретной информации используй Function Calling:
        - SearchAdmissionInfo: для поиска информации о поступлении по ключевым словам
        - Handover: если вопрос требует вмешательства живого оператора
        
        Если какая-то информация неясна или отсутствует, обязательно уточни детали у пользователя для 
        предоставления наиболее релевантной рекомендации.
        """
        
        assistant.update(instruction=instruction)
        print("Ассистент создан с инструментами!")
    else:
        # Создаем ассистента без индекса
        assistant = sdk.assistants.create(
            model, 
            ttl_days=1, 
            expiration_policy="since_last_active"
        )
        print("\nАссистент создан без индекса")
        
        assistant.update(
            instruction="""Ты - опытный работник приёмной комиссии университета МАИ, задача которого - консультировать пользователя в
            вопросах поступления в университет."""
        )
    
    return assistant 