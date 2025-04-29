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
import json

# Инициализация SDK для токенизации
sdk = initialize_sdk()
model = sdk.models.completions("yandexgpt", model_version="rc")

# Оптимальный размер чанка (примерно 2000 токенов)
CHUNK_SIZE = 2000 * 2  # 2000 токенов * 2 символа/токен

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
    
    # Разбиваем на строки
    lines = content.split("\n")
    chunks = []
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_size = len(line)
        if current_size + line_size > CHUNK_SIZE:
            # Загружаем текущий чанк
            chunk_content = "\n".join(current_chunk)
            chunk_id = sdk.files.upload_bytes(
                chunk_content.encode(),
                ttl_days=1,
                expiration_policy="static",
                mime_type="text/markdown"
            )
            chunks.append(chunk_id)
            
            # Начинаем новый чанк
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size
    
    # Загружаем последний чанк, если он не пустой
    if current_chunk:
        chunk_content = "\n".join(current_chunk)
        chunk_id = sdk.files.upload_bytes(
            chunk_content.encode(),
            ttl_days=1,
            expiration_policy="static",
            mime_type="text/markdown"
        )
        chunks.append(chunk_id)
    
    return chunks

def create_search_index(files, index_name):
    """Создание поискового индекса для группы файлов"""
    print(f"\nСоздание поискового индекса {index_name}...")
    
    op = sdk.search_indexes.create_deferred(
        files,
        index_type=HybridSearchIndexType(
            chunking_strategy=StaticIndexChunkingStrategy(
                max_chunk_size_tokens=2000,
                chunk_overlap_tokens=200
            ),
            combination_strategy=ReciprocalRankFusionIndexCombinationStrategy(),
        ),
    )
    index = op.wait()
    print(f"Индекс {index_name} создан!")
    
    return index

def get_wine_list():
    """Получение списка всех чатов"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(project_root, "data")
    
    wines = []
    for fn in glob(os.path.join(data_dir, "*", "*.md")):
        if os.path.isfile(fn):
            wine_name = os.path.splitext(os.path.basename(fn))[0]
            wines.append(wine_name)
    return sorted(wines)

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
    # Вывод списка чат
    print("\nСписок чатов:")
    for wine in get_wine_list():
        print(f"- {wine}")
    
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
        
        # Создание индексов для групп файлов
        indices = {}
        for year in [2021, 2022, 2023, 2024]:
            year_files = df[df["File"].str.contains(str(year))]["Uploaded"].explode()
            if not year_files.empty:
                index = create_search_index(year_files, f"index_{year}")
                indices[str(year)] = index.id
        
        # Сохранение ID индексов
        with open("indices.json", "w") as f:
            json.dump(indices, f)
        print("\nID индексов сохранены в indices.json")
