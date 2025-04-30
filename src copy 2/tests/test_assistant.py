"""
Скрипт для запуска многоагентного тестирования ассистента
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core.assistant import AdmissionsAssistant
from ..core.testing import ApplicantAgent, ParentAgent, run_test_dialog
from ..core.sdk import initialize_sdk

def main():
    # Инициализируем SDK
    sdk = initialize_sdk()
    
    # Создаем ассистента
    assistant = AdmissionsAssistant()
    assistant.start()
    
    # Создаем агентов
    applicant = ApplicantAgent(sdk=sdk)
    parent = ParentAgent(sdk=sdk)
    
    # Запускаем тесты
    print("\n=== Тестирование с абитуриентом ===")
    run_test_dialog(
        assistant,
        applicant,
        "Здравствуйте! Я хочу поступить в МАИ. Расскажите, пожалуйста, какие есть программы обучения?"
    )
    
    print("\n=== Тестирование с родителем ===")
    run_test_dialog(
        assistant,
        parent,
        "Добрый день! Мой ребенок хочет поступить в МАИ. Расскажите, пожалуйста, о перспективах трудоустройства после окончания?"
    )
    
    # Очищаем ресурсы
    assistant.cleanup()

if __name__ == "__main__":
    main() 