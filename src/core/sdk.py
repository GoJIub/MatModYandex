"""
Модуль для работы с Yandex Cloud SDK
"""

from ..utils.sdk_init import initialize_sdk
from ..utils.config import load_config
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from yandex_cloud_ml_sdk.search_indexes import (
    StaticIndexChunkingStrategy,
    HybridSearchIndexType,
    ReciprocalRankFusionIndexCombinationStrategy,
)
import json
import os
import pandas as pd

class SearchAdmissionInfo(BaseModel):
    """Поиск информации о поступлении"""
    query: str = Field(description="Поисковый запрос")
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
        # Берем первый индекс для начальной конфигурации
        index_id = list(indices.values())[0]
        print(f"\nАссистент использует индекс: {index_id}")
        
        # Получаем индекс
        index = sdk.search_indexes.get(index_id)
        
        # Создаем поисковый инструмент
        search_tool = sdk.tools.search_index(index)
        
        # Создаем ассистента с инструментом
        assistant = sdk.assistants.create(
            model, 
            ttl_days=1, 
            expiration_policy="since_last_active",
            tools=[search_tool]
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
        
        При ответе на вопросы:
        1. Используй поисковый инструмент для поиска информации
        2. Если информация найдена, обязательно укажи источник в ответе
        3. Если информация противоречива, указывай на это и проси уточнить детали
        4. Если информация не найдена, честно сообщай об этом
        
        Если какая-то информация неясна или отсутствует, обязательно уточни детали у пользователя для 
        предоставления наиболее релевантной рекомендации.
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
            instruction="""Ты - опытный работник приёмной комиссии университета МАИ, задача которого - консультировать пользователя в
            вопросах поступления в университет."""
        )
    
    return assistant

def get_search_tools(sdk) -> List[Dict]:
    """Получение всех поисковых инструментов"""
    if not os.path.exists("indices.json"):
        return []
        
    with open("indices.json", "r") as f:
        indices = json.load(f)
    
    search_tools = []
    for index_id in indices.values():
        index = sdk.search_indexes.get(index_id)
        search_tools.append(sdk.tools.search_index(index))
    
    return search_tools

def get_next_index(sdk, current_index_id: str) -> str:
    """Получение следующего индекса"""
    if not os.path.exists("indices.json"):
        return None
        
    with open("indices.json", "r") as f:
        indices = json.load(f)
    
    index_ids = list(indices.values())
    try:
        current_pos = index_ids.index(current_index_id)
        if current_pos + 1 < len(index_ids):
            return index_ids[current_pos + 1]
    except ValueError:
        pass
    
    return None

def print_citations(result):
    """Вывод источников информации из ответа ассистента"""
    for citation in result.citations:
        for source in citation.sources:
            if source.type != "filechunk":
                continue
            print("------------------------")
            print(source.parts[0]) 