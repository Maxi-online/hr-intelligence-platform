"""
AutoGPT File System Tool - Управление файлами

Обеспечивает AutoGPT агенту работу с файловой системой:
- Создание и редактирование файлов
- Чтение и анализ документов
- Сохранение результатов работы
- Безопасная работа в изолированной директории

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import aiofiles
import logging
import json
import csv
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import shutil
import hashlib

logger = logging.getLogger("file-manager")

class FileSystemTool:
    """
    Инструмент для работы с файловой системой
    
    Возможности:
    - Создание и редактирование файлов
    - Чтение различных форматов
    - Безопасная работа в изолированной директории
    - Резервное копирование важных файлов
    """
    
    def __init__(self, workspace_dir: Union[str, Path]):
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(exist_ok=True)
        
        # Создаем структуру директорий
        self.subdirs = {
            "reports": self.workspace / "reports",
            "data": self.workspace / "data", 
            "logs": self.workspace / "logs",
            "temp": self.workspace / "temp",
            "backups": self.workspace / "backups",
            "exports": self.workspace / "exports"
        }
        
        for subdir in self.subdirs.values():
            subdir.mkdir(exist_ok=True)
        
        # Статистика файловых операций
        self.stats = {
            "files_created": 0,
            "files_read": 0,
            "files_updated": 0,
            "files_deleted": 0,
            "total_operations": 0
        }
        
        logger.info(f"📁 File System Tool инициализирован в {self.workspace}")
    
    async def create_file(self, filename: str, content: str, 
                         subdirectory: str = None) -> Dict[str, Any]:
        """Создание нового файла"""
        try:
            # Определяем путь
            if subdirectory and subdirectory in self.subdirs:
                file_path = self.subdirs[subdirectory] / filename
            else:
                file_path = self.workspace / filename
            
            # Проверяем безопасность пути
            if not self._is_safe_path(file_path):
                raise ValueError(f"Небезопасный путь: {file_path}")
            
            # Создаем файл
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            # Обновляем статистику
            self.stats["files_created"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"📄 Файл создан: {file_path}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "size_bytes": len(content.encode('utf-8')),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания файла {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def read_file(self, filename: str, subdirectory: str = None) -> Dict[str, Any]:
        """Чтение файла"""
        try:
            # Определяем путь
            if subdirectory and subdirectory in self.subdirs:
                file_path = self.subdirs[subdirectory] / filename
            else:
                file_path = self.workspace / filename
            
            # Проверяем существование файла
            if not file_path.exists():
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            
            # Читаем файл
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Обновляем статистику
            self.stats["files_read"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"📖 Файл прочитан: {file_path}")
            
            return {
                "success": True,
                "content": content,
                "file_path": str(file_path),
                "size_bytes": len(content.encode('utf-8')),
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка чтения файла {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_file(self, filename: str, content: str, 
                         subdirectory: str = None, append: bool = False) -> Dict[str, Any]:
        """Обновление файла"""
        try:
            # Определяем путь
            if subdirectory and subdirectory in self.subdirs:
                file_path = self.subdirs[subdirectory] / filename
            else:
                file_path = self.workspace / filename
            
            # Создаем резервную копию если файл существует
            if file_path.exists():
                await self._create_backup(file_path)
            
            # Записываем файл
            mode = 'a' if append else 'w'
            async with aiofiles.open(file_path, mode, encoding='utf-8') as f:
                await f.write(content)
            
            # Обновляем статистику
            self.stats["files_updated"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"✏️ Файл обновлен: {file_path}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "operation": "append" if append else "overwrite",
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления файла {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_file(self, filename: str, subdirectory: str = None) -> Dict[str, Any]:
        """Удаление файла"""
        try:
            # Определяем путь
            if subdirectory and subdirectory in self.subdirs:
                file_path = self.subdirs[subdirectory] / filename
            else:
                file_path = self.workspace / filename
            
            # Проверяем существование файла
            if not file_path.exists():
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            
            # Создаем резервную копию перед удалением
            await self._create_backup(file_path)
            
            # Удаляем файл
            file_path.unlink()
            
            # Обновляем статистику
            self.stats["files_deleted"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"🗑️ Файл удален: {file_path}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "deleted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления файла {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_files(self, subdirectory: str = None, 
                        pattern: str = "*") -> Dict[str, Any]:
        """Список файлов в директории"""
        try:
            # Определяем директорию
            if subdirectory and subdirectory in self.subdirs:
                target_dir = self.subdirs[subdirectory]
            else:
                target_dir = self.workspace
            
            # Получаем список файлов
            files = []
            for file_path in target_dir.glob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "name": file_path.name,
                        "size_bytes": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": file_path.suffix
                    })
            
            # Сортируем по дате изменения
            files.sort(key=lambda x: x["modified"], reverse=True)
            
            logger.info(f"📋 Список файлов: {len(files)} файлов в {target_dir}")
            
            return {
                "success": True,
                "directory": str(target_dir),
                "files": files,
                "total_files": len(files)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка файлов: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_json(self, filename: str, data: Dict[str, Any], 
                       subdirectory: str = "data") -> Dict[str, Any]:
        """Сохранение данных в JSON"""
        try:
            json_content = json.dumps(data, ensure_ascii=False, indent=2)
            return await self.create_file(filename, json_content, subdirectory)
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения JSON: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def load_json(self, filename: str, subdirectory: str = "data") -> Dict[str, Any]:
        """Загрузка данных из JSON"""
        try:
            result = await self.read_file(filename, subdirectory)
            
            if result["success"]:
                data = json.loads(result["content"])
                return {
                    "success": True,
                    "data": data,
                    "file_info": {
                        "file_path": result["file_path"],
                        "size_bytes": result["size_bytes"]
                    }
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки JSON: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_csv(self, filename: str, data: List[Dict[str, Any]], 
                      subdirectory: str = "data") -> Dict[str, Any]:
        """Сохранение данных в CSV"""
        try:
            if not data:
                raise ValueError("Нет данных для сохранения")
            
            # Определяем путь
            file_path = self.subdirs[subdirectory] / filename
            
            # Записываем CSV
            async with aiofiles.open(file_path, 'w', newline='', encoding='utf-8') as f:
                # Получаем заголовки из первой записи
                fieldnames = list(data[0].keys())
                
                # Создаем содержимое CSV
                csv_content = []
                
                # Заголовок
                csv_content.append(','.join(fieldnames))
                
                # Данные
                for row in data:
                    values = []
                    for field in fieldnames:
                        value = str(row.get(field, ''))
                        # Экранируем запятые и кавычки
                        if ',' in value or '"' in value or '\n' in value:
                            value = '"' + value.replace('"', '""') + '"'
                        values.append(value)
                    csv_content.append(','.join(values))
                
                await f.write('\n'.join(csv_content))
            
            # Обновляем статистику
            self.stats["files_created"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"📊 CSV файл создан: {file_path}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "rows_saved": len(data),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения CSV: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_report(self, title: str, data: Dict[str, Any], 
                           format_type: str = "markdown") -> Dict[str, Any]:
        """Создание отчета в различных форматах"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.{format_type}"
            
            if format_type == "markdown":
                content = self._format_markdown_report(title, data)
            elif format_type == "json":
                content = json.dumps({
                    "title": title,
                    "created_at": datetime.now().isoformat(),
                    "data": data
                }, ensure_ascii=False, indent=2)
            else:
                content = self._format_text_report(title, data)
            
            return await self.create_file(filename, content, "reports")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания отчета: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_markdown_report(self, title: str, data: Dict[str, Any]) -> str:
        """Форматирование отчета в Markdown"""
        report = [
            f"# {title}",
            f"",
            f"**Создано:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"---",
            f""
        ]
        
        for key, value in data.items():
            report.append(f"## {key.replace('_', ' ').title()}")
            report.append("")
            
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    report.append(f"- **{subkey}:** {subvalue}")
            elif isinstance(value, list):
                for i, item in enumerate(value, 1):
                    report.append(f"{i}. {item}")
            else:
                report.append(str(value))
            
            report.append("")
        
        return "\n".join(report)
    
    def _format_text_report(self, title: str, data: Dict[str, Any]) -> str:
        """Форматирование отчета в текстовом формате"""
        report = [
            "=" * 50,
            title.upper(),
            "=" * 50,
            f"Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        for key, value in data.items():
            report.append(f"{key.replace('_', ' ').title()}:")
            report.append("-" * 30)
            
            if isinstance(value, (dict, list)):
                report.append(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                report.append(str(value))
            
            report.append("")
        
        return "\n".join(report)
    
    async def _create_backup(self, file_path: Path) -> None:
        """Создание резервной копии файла"""
        try:
            if file_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                backup_path = self.subdirs["backups"] / backup_name
                
                shutil.copy2(file_path, backup_path)
                logger.debug(f"💾 Создана резервная копия: {backup_path}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания резервной копии: {e}")
    
    def _is_safe_path(self, file_path: Path) -> bool:
        """Проверка безопасности пути"""
        try:
            # Проверяем что путь находится внутри рабочей директории
            file_path.resolve().relative_to(self.workspace.resolve())
            return True
        except ValueError:
            return False
    
    async def cleanup_temp_files(self, older_than_hours: int = 24) -> Dict[str, Any]:
        """Очистка временных файлов"""
        try:
            cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
            deleted_files = []
            
            for file_path in self.subdirs["temp"].iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_files.append(file_path.name)
            
            logger.info(f"🧹 Очищено {len(deleted_files)} временных файлов")
            
            return {
                "success": True,
                "deleted_files": deleted_files,
                "count": len(deleted_files)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки временных файлов: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_workspace_stats(self) -> Dict[str, Any]:
        """Статистика рабочего пространства"""
        try:
            stats = {
                "workspace_path": str(self.workspace),
                "subdirectories": {},
                "total_files": 0,
                "total_size_bytes": 0,
                "operations_stats": self.stats
            }
            
            for name, path in self.subdirs.items():
                if path.exists():
                    files = list(path.glob("*"))
                    file_count = len([f for f in files if f.is_file()])
                    size = sum(f.stat().st_size for f in files if f.is_file())
                    
                    stats["subdirectories"][name] = {
                        "file_count": file_count,
                        "size_bytes": size
                    }
                    
                    stats["total_files"] += file_count
                    stats["total_size_bytes"] += size
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {"error": str(e)}
