"""
Модуль для загрузки данных из Markdown файлов
"""

import os
from pathlib import Path
from typing import Dict, List

class DataLoader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        
    def load_wines(self) -> Dict[str, str]:
        """Загрузка информации о винах"""
        wines_dir = self.data_dir / "wines"
        return self._load_md_files(wines_dir)
        
    def load_regions(self) -> Dict[str, str]:
        """Загрузка информации о регионах"""
        regions_dir = self.data_dir / "regions"
        return self._load_md_files(regions_dir)
        
    def _load_md_files(self, directory: Path) -> Dict[str, str]:
        """Загрузка всех MD файлов из директории"""
        if not directory.exists():
            return {}
            
        data = {}
        for file_path in directory.glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                data[file_path.stem] = f.read()
                
        return data 