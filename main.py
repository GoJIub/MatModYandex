from utils import initialize_sdk, create_thread, create_assistant
from config import CONFIG

def main():
    # Инициализация SDK
    sdk = initialize_sdk()
    
    # Создание диалога и ассистента
    thread = create_thread(sdk)
    assistant = create_assistant(sdk, thread)
    
    print("Начало диалога (для выхода введите 'exit' или 'quit')")
    
    while True:
        # Получение сообщения от пользователя
        user_input = input("\nВы: ").strip()
        
        if user_input.lower() in ['exit', 'quit']:
            break
            
        # Отправка сообщения и получение ответа
        thread.write(user_input)
        run = assistant.run(thread)
        result = run.wait()
        print("\nАссистент:", result.text)
    
    # Очистка ресурсов
    thread.delete()
    assistant.delete()
    print("\nДиалог завершен")

if __name__ == "__main__":
    main()
