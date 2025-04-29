"""
Модуль с основной логикой ассистента
"""

from ..utils.config import load_config
from .sdk import initialize_sdk, create_thread, create_assistant, SearchAdmissionInfo, Handover
import time

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
        if not self.thread or not self.assistant:
            raise RuntimeError("Ассистент не инициализирован. Вызовите метод start()")
            
        self.thread.write(question)
        run = self.assistant.run(self.thread)
        result = run.wait()
        
        # Обработка вызовов функций
        if result.tool_calls:
            tool_results = []
            for tool_call in result.tool_calls:
                print(f"Обработка вызова функции: {tool_call.function.name}")
                
                if tool_call.function.name == "SearchAdmissionInfo":
                    # Обработка поиска информации о поступлении
                    search_params = SearchAdmissionInfo.model_validate(tool_call.function.arguments)
                    # TODO: Реализовать поиск по базе данных
                    tool_results.append({
                        "name": tool_call.function.name,
                        "content": f"Найдена информация по запросу: {search_params.query}"
                    })
                
                elif tool_call.function.name == "Handover":
                    # Обработка передачи оператору
                    handover_params = Handover.model_validate(tool_call.function.arguments)
                    tool_results.append({
                        "name": tool_call.function.name,
                        "content": handover_params.process(self.thread)
                    })
            
            # Отправляем результаты выполнения функций
            run.submit_tool_results(tool_results)
            time.sleep(1)  # Даем время на обработку
            result = run.wait()
            
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
            print("Ассистент:", answer)
        except Exception as e:
            print("Ошибка:", e)