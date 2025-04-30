"""
Модуль для многоагентного тестирования ассистента
"""

from yandex_cloud_ml_sdk import YCloudML

class Agent:
    """Базовый класс для агентов тестирования"""
    def __init__(self, sdk: YCloudML, instruction: str):
        self.sdk = sdk
        self.instruction = instruction
        self.thread = self.sdk.threads.create()
        self.assistant = self.sdk.assistants.create(
            self.sdk.models.completions("yandexgpt", model_version="rc"),
            instruction=self.instruction
        )
    
    def __call__(self, message: str) -> str:
        """Обработка сообщения агентом"""
        self.thread.write(message)
        run = self.assistant.run(self.thread)
        result = run.wait()
        return result.text

class ApplicantAgent(Agent):
    """Агент-абитуриент для тестирования"""
    def __init__(self, sdk: YCloudML):
        instruction = """
        Ты - абитуриент, который хочет поступить в МАИ. Ты не очень хорошо разбираешься в правилах поступления,
        но хочешь получить подробную консультацию. Задавай конкретные вопросы о:
        - Программах обучения
        - Вступительных испытаниях
        - Проходных баллах
        - Сроках подачи документов
        - Особенностях поступления
        
        Говори простым языком, короткими фразами. Если тебе что-то непонятно, проси объяснить подробнее.
        Когда получишь полную информацию, попроси соединить с оператором для уточнения деталей.
        Пиши простым языком, короткими фразами.
        """
        super().__init__(sdk, instruction)

class ParentAgent(Agent):
    """Агент-родитель для тестирования"""
    def __init__(self, sdk: YCloudML):
        instruction = """
        Ты - родитель абитуриента, который хочет поступить в МАИ. Ты беспокоишься о будущем своего ребенка
        и хочешь получить подробную информацию о:
        - Перспективах трудоустройства
        - Стоимости обучения
        - Условиях проживания
        - Военной кафедре
        - Международных программах
        
        Задавай вопросы вежливо, но настойчиво. Если ответы кажутся неполными, проси уточнить детали.
        В конце диалога попроси соединить с оператором для обсуждения конкретных условий поступления.
        Пиши простым языком, короткими фразами.
        """
        super().__init__(sdk, instruction)

def run_test_dialog(assistant, agent, initial_message: str, max_turns: int = 10) -> bool:
    """
    Запуск тестового диалога между ассистентом и агентом
    
    Args:
        assistant: Ассистент для тестирования
        agent: Агент для взаимодействия
        initial_message: Начальное сообщение
        max_turns: Максимальное количество ходов
        
    Returns:
        bool: True если диалог завершился успешно
    """
    print(f"\nНачало тестового диалога с {agent.__class__.__name__}")
    print("-" * 50)
    
    msg = initial_message
    handover = False
    
    for i in range(max_turns):
        print(f"\nХод {i+1}")
        print(f"Агент: {msg}")
        
        # Получаем ответ ассистента
        try:
            response = assistant.ask(msg)
            print(f"Ассистент: {response}")
            
            # Проверяем на запрос передачи оператору
            if "оператор" in response.lower() or "приемная комиссия" in response.lower():
                handover = True
                break
                
            # Получаем следующий вопрос от агента
            msg = agent(response)
            
        except Exception as e:
            print(f"Ошибка в ходе диалога: {e}")
            return False
            
    print("\nДиалог завершен")
    print(f"Передача оператору: {'Да' if handover else 'Нет'}")
    return True