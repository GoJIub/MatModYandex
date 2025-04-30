"""
Модуль для работы с Yandex Cloud SDK
"""

from ..utils.sdk_init import initialize_sdk
from ..utils.config import load_config
from pydantic import BaseModel, Field
from typing import Optional, List
from yandex_cloud_ml_sdk.search_indexes import (
    StaticIndexChunkingStrategy,
    HybridSearchIndexType,
    ReciprocalRankFusionIndexCombinationStrategy,
)
from dotenv import load_dotenv
import os
import telebot
from telebot import types
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)

# Глобальные переменные
bot = None
calling_admin = {}

def set_bot(bot_instance):
    """Установка экземпляра бота для использования в классе Handover"""
    global bot
    bot = bot_instance

load_dotenv()

class SearchAdmissionInfo(BaseModel):
    """Поиск информации о поступлении"""
    query: str = Field(description="Поисковый запрос")
    program: Optional[str] = Field(description="Программа обучения", default=None)

class Handover(BaseModel):
    """Эта функция позволяет передать диалог оператору приёмной комиссии"""
    reason: str = Field(
        description="Причина для вызова оператора", 
        default="не указана"
    )

    @staticmethod
    def _to_proto(proto_class):
        """Преобразование в прототип для SDK"""
        tool = proto_class()
        tool.function.name = "handover_to_operator"
        tool.function.description = "Передача диалога оператору приёмной комиссии"
        tool.function.parameters = {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Причина для вызова оператора"
                }
            },
            "required": ["reason"]
        }
        return tool

    def process(self, thread):
        try:
            logger.info(f"\n[DEBUG] Передача диалога оператору:")
            logger.info(f"thread_id: {thread.id}")
            
            # Пытаемся разблокировать поток, если он заблокирован
            if hasattr(thread, 'current_run') and thread.current_run:
                logger.info(f"[DEBUG] Поток заблокирован, пытаемся разблокировать...")
                try:
                    thread.current_run.cancel()
                    logger.info(f"[DEBUG] Поток успешно разблокирован")
                except Exception as e:
                    logger.error(f"[DEBUG] Ошибка при разблокировке потока: {e}")
            
            # Завершаем работу ассистента
            if hasattr(thread, 'assistant'):
                try:
                    thread.assistant.delete()
                    logger.info(f"[DEBUG] Ассистент удален")
                except Exception as e:
                    logger.error(f"[DEBUG] Ошибка при удалении ассистента: {e}")
            
            # Получаем список всех админов
            admins = get_all_admin_ids()
            logger.info(f"[DEBUG] Найдены админы: {admins}")
            
            if not admins:
                return "К сожалению, сейчас нет доступных операторов. Попробуйте позже."
            
            # Добавляем пользователя в очередь
            queue_position = stay_in_quire(thread.user_id)
            if queue_position is None:
                return "Произошла ошибка при добавлении в очередь. Пожалуйста, попробуйте позже."
            
            # Отправляем сообщение всем админам
            for admin_id in admins:
                try:
                    markup = types.InlineKeyboardMarkup()
                    button_agree = types.InlineKeyboardButton(
                        '✅Подтвердить',
                        callback_data=f'confirm_{thread.user_id}'
                    )
                    markup.add(button_agree)
                    text = f'С вами хочет связаться пользователь {thread.user_id}.'
                    mes_id = bot.send_message(admin_id, text, reply_markup=markup)
                    calling_admin[admin_id] = mes_id.message_id
                    logger.info(f"[DEBUG] Отправлено сообщение админу {admin_id}")
                except Exception as e:
                    logger.error(f"[ERROR] Ошибка при отправке сообщения админу {admin_id}: {e}")
            
            # Отправляем пользователю сообщение о его позиции в очереди
            text = 'Заявка отправлена администраторам, пожалуйста ожидайте. \n\nА пока можете послушать музыку:'
            markup = types.InlineKeyboardMarkup()
            button_text = 'Узнать положение в очереди'
            button_agree = types.InlineKeyboardButton(button_text, callback_data='queue_position')
            markup.add(button_agree)
            bot.send_message(thread.user_id, text, reply_markup=markup)
            
            # Воспроизводим музыку во время ожидания
            music_path = get_random_music()
            if music_path:
                with open(music_path, 'rb') as audio_file:
                    bot.send_audio(thread.user_id, audio_file)
            else:
                bot.send_message(thread.user_id, "К сожалению, музыкальные треки временно недоступны")
                logger.warning("No music files available")
            
            return "Сейчас я передам ваш запрос оператору. Пожалуйста, ожидайте ответа."
            
        except Exception as e:
            error_msg = f"Произошла ошибка при передаче запроса оператору. Пожалуйста, попробуйте позже."
            logger.error(f"[DEBUG] Ошибка при передаче оператору: {e}")
            return error_msg

class AddToFavorites(BaseModel):
    """Добавление программы в список интересов"""
    program: str = Field(description="Название программы обучения")
    
    def process(self, thread):
        print(f"\n[DEBUG] Вызов функции AddToFavorites с параметрами:")
        print(f"program: {self.program}")
        print(f"thread_id: {thread.id}")
        
        if not hasattr(thread, 'favorites'):
            thread.favorites = []
        if self.program not in thread.favorites:
            thread.favorites.append(self.program)
            result = f"Программа '{self.program}' добавлена в список интересов."
        else:
            result = f"Программа '{self.program}' уже есть в списке интересов."
            
        print(f"[DEBUG] Результат функции AddToFavorites: {result}")
        return result

class ShowFavorites(BaseModel):
    """Просмотр списка интересных программ"""
    
    def process(self, thread):
        print(f"\n[DEBUG] Вызов функции ShowFavorites:")
        print(f"thread_id: {thread.id}")
        
        if not hasattr(thread, 'favorites') or not thread.favorites:
            result = "У вас пока нет программ в списке интересов."
        else:
            result = "Ваши интересующие программы:\n" + "\n".join(f"- {program}" for program in thread.favorites)
            
        print(f"[DEBUG] Результат функции ShowFavorites: {result}")
        return result

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
        
        # Создаем ассистента с инструментами
        assistant = sdk.assistants.create(
            model, 
            ttl_days=1, 
            expiration_policy="since_last_active",
            tools=[search_tool, Handover]
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
        
        3. Факты о МАИ, собранные от студентов, структурированные по темам:
           - Учебный процесс
           - Инфраструктура
           - Студенческая жизнь
           - История и уникальность
           - Международные возможности
        
        4. Официальные документы и нормативные акты:
           - Постановление Правительства РФ о целевом обучении
           - Федеральный закон об образовании
           - Правила приема в МАИ
           - Вопросы и ответы по поступлению
        
        Пытайся использовать максимально новую информацию.
        В приоритете используй информацию из официальных документов.

        Твои основные задачи:
        - Давать точные и актуальные ответы на вопросы абитуриентов
        - Проактивно предлагать оптимальные программы обучения и стратегии поступления
        - При необходимости запрашивать дополнительную информацию для более точной консультации
        - Вести диалог в вежливом и профессиональном тоне
        - Использовать факты от студентов для более живого и достоверного описания жизни в МАИ
        
        При ответе на вопросы:
        1. Используй поисковый инструмент для поиска информации
        2. Если информация найдена, обязательно укажи источник в ответе
        3. Если информация противоречива, указывай на это и проси уточнить детали
        4. Если информация не найдена, честно сообщай об этом
        5. При возможности, дополняй ответы реальными фактами от студентов
        
        В начале диалога (при команде /start):
        1. Поприветствуй абитуриента
        2. Спроси о его интересах и целях
        3. Предложи несколько подходящих программ обучения
        4. Расскажи о преимуществах МАИ, используя факты от студентов
        5. Предложи оптимальную стратегию поступления
        
        При запросе на вызов оператора или администратора:
        - Если пользователь просит оператора, администратора или использует фразы типа "позови админа", "переведи на оператора", 
          "нужен оператор" и т.п., немедленно вызови функцию Handover
        - В качестве причины укажи краткое описание запроса пользователя
        - Не задавай уточняющих вопросов о причине вызова
        - Не пытайся самостоятельно решить проблему
        - Просто передай запрос оператору
        
        Важные правила проверки информации:
        1. Перед отправкой ответа всегда проверяй его на:
           - Достоверность (соответствие официальным данным)
           - Актуальность (соответствие текущему году)
           - Полноту (все важные детали учтены)
           - Противоречия (отсутствие противоречий с ранее предоставленной информацией)
        
        2. Если есть сомнения в достоверности информации:
           - Укажи на это в ответе
           - Предложи уточнить информацию у оператора
           - Используй фразы типа "насколько мне известно", "согласно имеющимся данным"
        
        3. При работе с фактами от студентов:
           - Указывай, что это субъективные мнения
           - Не выдавай их за официальную информацию
           - Используй их для иллюстрации, а не как основной источник
        
        4. При работе с историческими данными:
           - Указывай год или период, к которому относится информация
           - Отмечай, если данные могли устареть
           - Предлагай уточнить актуальность у оператора
        
        5. При работе с официальными документами:
           - Используй точные формулировки из документов
           - Указывай источник (например, "согласно Постановлению Правительства РФ...")
           - При необходимости объясняй сложные термины простым языком
           - Если информация из разных документов дополняет друг друга, объединяй её в единый ответ
        
        Если какая-то информация неясна или отсутствует, обязательно уточни детали у пользователя для 
        предоставления наиболее релевантной рекомендации.

        Прими к сведению:
            - Некоторые словосочетания могут быть сокращены. Например: приёмка - приёмная комиссия.
            - Пользователь может допускать ошибки при написании слов. В этом случае, попробуй понять, 
              что он имел в виду, и поискать ответ на его вопрос в доступной тебе базе знаний.
        """
        
        assistant.update(instruction=instruction)
        print("Ассистент создан с поисковым инструментом и функцией передачи оператору!")
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