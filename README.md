# Wine Assistant

Ассистент для консультаций по винам на базе Yandex Cloud ML.

## Структура проекта

```
AdvancedAssistant/
├── data/                    # Данные
│   ├── wines/              # Информация о винах
│   └── regions/            # Информация о регионах
├── src/                    # Исходный код
│   ├── core/              # Основная логика
│   ├── data/              # Работа с данными
│   └── utils/             # Вспомогательные функции
├── tests/                 # Тесты
├── notebooks/            # Jupyter notebooks
├── .env                  # Переменные окружения
└── requirements.txt      # Зависимости
```

## Установка

1. Клонируйте репозиторий:
```bash
git clone <url-репозитория>
cd AdvancedAssistant
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/Scripts/activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env`:
```
folder_id=ваш_folder_id
api_key=ваш_api_key
```

## Использование

### Через Python

```python
from src.core.assistant import WineAssistant

assistant = WineAssistant()
assistant.start()

response = assistant.ask("Какое вино выбрать к стейку?")
print(response)

assistant.cleanup()
```

### Через Jupyter Notebook

Откройте `notebooks/assistant_demo.ipynb` в Jupyter Notebook.

## Разработка

### Добавление новых данных

1. Создайте Markdown файл в соответствующей директории:
   - `data/wines/` для информации о винах
   - `data/regions/` для информации о регионах

2. Файл должен содержать структурированную информацию в формате Markdown

### Запуск тестов

```bash
pytest tests/
```

## Требования

- Python 3.8+
- Доступ к Yandex Cloud ML API
- Установленные зависимости из requirements.txt 