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

# Инициализация SDK для токенизации
sdk = initialize_sdk()
model = sdk.models.completions("yandexgpt", model_version="rc")

def get_token_count(filename):
    """Подсчёт количества токенов в файле"""
    with open(filename, "r", encoding="utf8") as f:
        return len(model.tokenize(f.read()))

def get_file_len(filename):
    """Подсчёт количества символов в файле"""
    with open(filename, encoding="utf-8") as f:
        l = len(f.read())
    return l

def upload_file(filename):
    """Загрузка файла в облако"""
    return sdk.files.upload(filename, ttl_days=1, expiration_policy="static")

def create_search_index(df):
    """Создание поискового индекса"""
    print("\nСоздание поискового индекса...")
    
    # Создаем индекс для вин
    op = sdk.search_indexes.create_deferred(
        df[df["Category"] == "wines"]["Uploaded"],
        index_type=HybridSearchIndexType(
            chunking_strategy=StaticIndexChunkingStrategy(
                max_chunk_size_tokens=1000, chunk_overlap_tokens=100
            ),
            combination_strategy=ReciprocalRankFusionIndexCombinationStrategy(),
        ),
    )
    index = op.wait()
    print("Индекс для вин создан!")
    
    # Добавляем файлы регионов
    op = index.add_files_deferred(df[df["Category"]=="regions"]["Uploaded"])
    xfiles = op.wait()
    print("Файлы регионов добавлены в индекс!")
    
    return index

def get_wine_list():
    """Получение списка всех вин"""
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
    # Вывод списка вин
    print("\nСписок вин:")
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
        
        # Загрузка файлов в облако
        print("\nЗагрузка файлов в облако...")
        df["Uploaded"] = df["File"].apply(upload_file)
        print("\nЗагруженные файлы:")
        for _, row in df.iterrows():
            print(f"- {row['File']} -> {row['Uploaded'].id}")
        print("Файлы загружены!")
        
        # Создание поискового индекса
        index = create_search_index(df)
        print(f"\nИндекс создан с ID: {index.id}")
        
        # Сохранение ID индекса
        save_search_index_id(index.id)
        print("ID индекса сохранен в конфигурации")
