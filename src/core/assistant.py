"""
Модуль с основной логикой ассистента
"""

from ..utils.config import load_config
from .sdk import initialize_sdk, create_thread, create_assistant, get_next_index, get_search_tools
import time
import os
import json

class AdmissionsAssistant:
    def __init__(self):
        self.config = load_config()
        self.sdk = initialize_sdk()
        self.thread = None
        self.assistant = None
        self.current_index_id = None
        
    def start(self):
        """Инициализация диалога с ассистентом"""
        self.thread = create_thread(self.sdk)
        self.assistant = create_assistant(self.sdk, self.thread)
        return "Ассистент готов к работе!"
        
    def ask(self, question: str) -> str:
        """Задать вопрос ассистенту"""
        if not self.thread or not self.assistant:
            raise RuntimeError("Ассистент не инициализирован. Вызовите метод start()")
        
        # Получаем все доступные индексы
        indices = {}
        if os.path.exists("indices.json"):
            with open("indices.json", "r") as f:
                indices = json.load(f)
        
        if not indices:
            print("Не найдены индексы для поиска")
            return "Извините, но я не могу найти информацию в базе данных."
        
        # Начинаем с первого индекса
        self.current_index_id = list(indices.values())[0]
        index = self.sdk.search_indexes.get(self.current_index_id)
        search_tool = self.sdk.tools.search_index(index)
        
        # Создаем нового ассистента с текущим инструментом
        model = self.sdk.models.completions("yandexgpt", model_version="rc")
        self.assistant = self.sdk.assistants.create(
            model, 
            ttl_days=1, 
            expiration_policy="since_last_active",
            tools=[search_tool]
        )
        
        # Обновляем инструкцию для ассистента
        instruction = f"""
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
        
        ВАЖНО: Если ты не нашел информацию в текущем индексе, обязательно сообщи об этом, используя одну из следующих фраз:
        - "Не нашел ответ в текущем индексе"
        - "Не нашел информацию в текущем индексе"
        - "Информация не найдена в текущем индексе"
        - "Нет информации в текущем индексе"
        - "Не могу найти информацию в текущем индексе"
        - "Не удалось найти информацию в текущем индексе"
        
        Это позволит системе переключиться на следующий индекс для поиска информации.
        
        Если какая-то информация неясна или отсутствует, обязательно уточни детали у пользователя для 
        предоставления наиболее релевантной рекомендации.
        """
        
        self.assistant.update(instruction=instruction)
        
        # Задаем вопрос
        self.thread.write(question)
        run = self.assistant.run(self.thread)
        result = run.wait()
        
        # Проверяем ответ и переключаемся на следующий индекс, если нужно
        while True:
            # Проверяем, есть ли в ответе явное указание на отсутствие информации
            if any(phrase in result.text.lower() for phrase in [
                "не нашел ответ в текущем индексе",
                "не нашел информацию в текущем индексе",
                "информация не найдена в текущем индексе",
                "нет информации в текущем индексе",
                "не могу найти информацию в текущем индексе",
                "не удалось найти информацию в текущем индексе"
            ]):
                # Пробуем следующий индекс
                next_index_id = get_next_index(self.sdk, self.current_index_id)
                if next_index_id:
                    print(f"\nПереключение на следующий индекс: {next_index_id}")
                    index = self.sdk.search_indexes.get(next_index_id)
                    search_tool = self.sdk.tools.search_index(index)
                    
                    # Создаем нового ассистента с новым инструментом
                    self.assistant = self.sdk.assistants.create(
                        model, 
                        ttl_days=1, 
                        expiration_policy="since_last_active",
                        tools=[search_tool]
                    )
                    
                    # Обновляем инструкцию для нового ассистента
                    self.assistant.update(instruction=instruction)
                    
                    self.current_index_id = next_index_id
                    
                    # Повторяем вопрос с новым индексом
                    self.thread.write(question)
                    run = self.assistant.run(self.thread)
                    result = run.wait()
                    continue
                else:
                    print("\nДостигнут конец списка индексов")
                    break
            else:
                break
        
        return result.text
        
    def cleanup(self):
        """Очистка ресурсов"""
        if self.thread:
            self.thread.delete()
        if self.assistant:
            self.assistant.delete()

if __name__ == "__main__":
    assistant = AdmissionsAssistant()
    print(assistant.start())
    print("Введите вопрос (или 'exit' для выхода):")
    while True:
        question = input("> ")
        if question.lower() in ("exit", "quit", "выход"):
            print("Завершение работы ассистента.")
            assistant.cleanup()
            break
        try:
            answer = assistant.ask(question)
            print("\nАссистент:", answer)
        except Exception as e:
            print("Ошибка:", e)