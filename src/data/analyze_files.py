"""
Модуль для анализа текстовых файлов
"""

from glob import glob
from tqdm.auto import tqdm
import pandas as pd
from ..utils.sdk_init import initialize_sdk
from ..utils.config import save_search_index_id
from yandex_cloud_ml_sdk.search_indexes import (
    StaticIndexChunkingStrategy,
    HybridSearchIndexType,
    ReciprocalRankFusionIndexCombinationStrategy,
)
import os
from dotenv import set_key

# Инициализация SDK для токенизации
sdk = initialize_sdk()
model = sdk.models.completions("yandexgpt", model_version="rc")

# Оптимальный размер чанка (1000 токенов)
CHUNK_SIZE = 1000 * 2  # 1000 токенов * 2 символа/токен

def get_token_count(filename):
    """Подсчёт количества токенов в файле"""
    with open(filename, "r", encoding="utf8") as f:
        content = f.read()
        tokens = len(model.tokenize(content))
        chars = len(content)
        ratio = chars / tokens
        print(f"{os.path.basename(filename)}: {tokens} токенов, {ratio:.2f} chars/token")
        return tokens

def get_file_len(filename):
    """Подсчёт количества символов в файле"""
    with open(filename, encoding="utf-8") as f:
        l = len(f.read())
    return l

def chunk_and_upload_file(filename):
    """Разбиение файла на чанки и загрузка в облако"""
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Пропускаем заголовок и начало таблицы
    lines = content.split("\n")
    if lines[0].startswith("#"):
        year = lines[0].strip("#").strip()
        lines = lines[1:]
    else:
        year = "unknown"
        
    if lines[0].startswith("| Вопросы | Ответы |"):
        lines = lines[2:]  # Пропускаем заголовок таблицы и разделитель
    
    # Разбиваем на диалоги
    chunks = []
    
    for line in lines:
        if not line.strip():  # Пропускаем пустые строки
            continue
            
        # Разделяем строку на вопрос и ответ
        parts = line.split("|")
        if len(parts) < 4:  # Пропускаем некорректные строки
            continue
            
        # Извлекаем ID и дату из вопроса
        question_parts = parts[1].strip().split("<br>")
        if len(question_parts) > 1:
            metadata = question_parts[0].strip()
            question = question_parts[1].strip()
        else:
            metadata = ""
            question = parts[1].strip()
            
        # Извлекаем ID и дату из ответа
        answer_parts = parts[2].strip().split("<br>")
        if len(answer_parts) > 1:
            answer_metadata = answer_parts[0].strip()
            answer = answer_parts[1].strip()
        else:
            answer_metadata = ""
            answer = parts[2].strip()
        
        # Форматируем диалог с метаданными
        dialog = f"""Год: {year}
Вопрос ({metadata}):
{question}

Ответ ({answer_metadata}):
{answer}"""
        
        # Загружаем каждый диалог как отдельный чанк
        chunk_id = sdk.files.upload_bytes(
            dialog.encode(),
            ttl_days=1,
            expiration_policy="static",
            mime_type="text/markdown"
        )
        chunks.append(chunk_id)
    
    return chunks

def create_and_populate_search_index(chunks, index_name, batch_size=100):
    """Создание поискового индекса и добавление чанков пакетами"""
    if not chunks:
        raise ValueError("No chunks provided for indexing")
    
    print(f"\nСоздание поискового индекса...")
    
    # Создаем индекс с первым пакетом чанков (до batch_size)
    initial_batch = chunks[:batch_size]
    op = sdk.search_indexes.create_deferred(
        initial_batch,
        index_type=HybridSearchIndexType(
            chunking_strategy=StaticIndexChunkingStrategy(
                max_chunk_size_tokens=1000,
                chunk_overlap_tokens=100
            ),
            combination_strategy=ReciprocalRankFusionIndexCombinationStrategy(),
        ),
    )
    index = op.wait()
    print(f"Индекс {index_name} создан с первым пакетом ({len(initial_batch)} чанков)!")
    
    # Добавляем оставшиеся чанки пакетами
    for i in range(batch_size, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        print(f"Добавление пакета {(i//batch_size) + 1} ({len(batch)} чанков)...")
        op = index.add_files_deferred(batch)
        op.wait()
        print(f"Пакет {(i//batch_size) + 1} добавлен!")
    
    print(f"Индекс {index_name} полностью заполнен!")
    return index

def get_chat_files():
    """Получение списка всех чатов"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(project_root, "data")
    
    files = []
    for fn in glob(os.path.join(data_dir, "chats", "*.md")):
        if os.path.isfile(fn):
            files.append(fn)
    return sorted(files)

def analyze_files():
    """Анализ всех .md файлов в директории data"""
    # Получаем путь к корню проекта
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(project_root, "data")
    
    print("\nАнализ соотношения токенов и символов:")
    d = [
        {
            "File": fn,
            "Tokens": get_token_count(fn),
            "Chars": get_file_len(fn),
            "Category": os.path.basename(os.path.dirname(fn)),
        }
        for fn in glob(os.path.join(data_dir, "*", "*.md"))
        if os.path.isfile(fn)
    ]
    return pd.DataFrame(d)

if __name__ == "__main__":
    # Вывод списка чатов
    print("\nСписок чатов:")
    for file in get_chat_files():
        print(f"- {file}")
    
    # Анализ файлов
    df = analyze_files()
    if df.empty:
        print("\nФайлы не найдены. Проверьте путь к директории data.")
    else:
        print("\nРезультаты анализа файлов:")
        print(df)
        print(df.groupby("Category").agg({"Tokens": ("min", "mean", "max")}))
        
        # Загрузка файлов в облако с чанкованием
        print("\nЗагрузка файлов в облако с чанкованием...")
        df["Uploaded"] = df["File"].apply(chunk_and_upload_file)
        print("\nЗагруженные чанки:")
        for _, row in df.iterrows():
            print(f"- {row['File']} -> {len(row['Uploaded'])} чанков")
        print("Файлы загружены!")
        
        # Создание и заполнение индекса
        all_chunks = df["Uploaded"].explode().tolist()
        index = create_and_populate_search_index(all_chunks, f"index_1")
        
        # Сохранение ID индекса в .env
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        set_key(env_file, "SEARCH_INDEX_ID", index.id)
        print("\nID индекса сохранён в .env")