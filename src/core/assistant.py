"""
Модуль с основной логикой ассистента
"""

from ..utils.config import load_config
from .sdk import initialize_sdk, create_thread, create_assistant

class WineAssistant:
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
        return result.text
        
    def cleanup(self):
        """Очистка ресурсов"""
        if self.thread:
            self.thread.delete()
        if self.assistant:
            self.assistant.delete()

if __name__ == "__main__":
    assistant = WineAssistant()
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