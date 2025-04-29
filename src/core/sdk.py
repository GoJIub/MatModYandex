"""
Модуль для работы с Yandex Cloud SDK
"""

from ..utils.sdk_init import initialize_sdk
from ..utils.config import load_config
from pydantic import BaseModel, Field
from typing import Optional
from yandex_cloud_ml_sdk.search_indexes import (
    StaticIndexChunkingStrategy,
    HybridSearchIndexType,
    ReciprocalRankFusionIndexCombinationStrategy,
)
from dotenv import load_dotenv
import os

load_dotenv()

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
    
    # Загружаем ID индекса из .env
    index_id = os.getenv("SEARCH_INDEX_ID")
    
    if index_id:
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

def print_citations(result):
    """Вывод источников информации из ответа ассистента"""
    for citation in result.citations:
        for source in citation.sources:
            if source.type != "filechunk":
                continue
            print("------------------------")
            print(source.parts[0])

def search_admissions_info(sdk, query: str) -> list:
    """Поиск информации о поступлении"""
    try:
        # Получаем ID индекса из переменных окружения
        index_id = os.getenv("SEARCH_INDEX_ID")
        if not index_id:
            print("Ошибка: SEARCH_INDEX_ID не найден в переменных окружения")
            return []
            
        # Получаем индекс
        index = sdk.search_indexes.get(index_id)
        if not index:
            print(f"Ошибка: индекс {index_id} не найден")
            return []
            
        # Выполняем поиск
        search_results = index.search(
            query=query,
            limit=5,
            score_threshold=0.5
        )
        
        # Форматируем результаты
        results = []
        for result in search_results:
            results.append({
                "text": result.text,
                "score": result.score,
                "metadata": result.metadata
            })
            
        return results
        
    except Exception as e:
        print(f"Ошибка при поиске: {e}")
        return []