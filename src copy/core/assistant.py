"""
Модуль с основной логикой ассистента
"""

from ..utils.config import load_config
from .sdk import initialize_sdk, create_thread, create_assistant, Handover
from dotenv import load_dotenv
import os
import logging
import json

# Инициализация логгера
logger = logging.getLogger(__name__)

load_dotenv()

class AdmissionsAssistant:
    def __init__(self):
        self.config = load_config()
        self.sdk = initialize_sdk()
        self.thread = None
        self.assistant = None
        
    def start(self):
        """Инициализация диалога с ассистентом"""
        self.thread = create_thread(self.sdk)
        self.assistant = create_assistant(self.sdk, self.thread)
        return "Ассистент готов к работе!"
        
    def ask(self, question: str) -> str:
        """Задать вопрос ассистенту"""
        try:
            # Создаем новый поток для каждого запроса
            logger.info("[DEBUG] Создание нового потока для запроса")
            self.thread = create_thread(self.sdk)
            
            # Задаем вопрос
            logger.info(f"Отправка вопроса ассистенту: {question}")
            self.thread.write(question)
            run = self.assistant.run(self.thread)
            result = run.wait()
            
            # Логируем полученный результат
            logger.info(f"Получен ответ от ассистента: {result}")
            
            # Проверяем, является ли ответ вызовом функции
            if hasattr(result, 'tool_calls') and result.tool_calls:
                logger.info(f"Получен вызов функции: {result.tool_calls}")
                try:
                    # Получаем первый вызов функции
                    tool_call = result.tool_calls[0]
                    if tool_call.function.name == 'handover_to_operator':
                        # Создаем экземпляр Handover и вызываем process
                        handover = Handover(reason=tool_call.function.arguments.get('reason', 'не указана'))
                        return {
                            'function_call': {
                                'name': 'handover_to_operator',
                                'arguments': tool_call.function.arguments
                            }
                        }
                    else:
                        logger.warning(f"Неизвестный вызов функции: {tool_call.function.name}")
                        return "Извините, произошла ошибка при обработке запроса."
                except Exception as e:
                    logger.error(f"Ошибка при обработке вызова функции: {e}")
                    return "Произошла ошибка при обработке запроса. Попробуйте позже."
            
            # Если это обычный ответ
            if hasattr(result, 'text') and result.text:
                logger.info(f"Получен текстовый ответ: {result.text}")
                return result.text
            else:
                logger.warning("Получен пустой ответ от ассистента")
                return "Извините, я не смог обработать ваш запрос. Попробуйте переформулировать вопрос."
                
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}")
            return "Произошла ошибка при обработке вашего запроса. Попробуйте позже."
        
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