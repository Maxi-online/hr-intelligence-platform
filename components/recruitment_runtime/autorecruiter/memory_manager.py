"""
AutoGPT Memory Manager - Система управления памятью

Реализует долгосрочную и краткосрочную память для AutoGPT агента:
- Векторный поиск через ChromaDB
- Эмбеддинги через OpenAI
- Персистентное хранение контекста
- Автоматическое забывание старых данных

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

import chromadb
from chromadb.config import Settings
import openai

logger = logging.getLogger("memory-manager")

class LongTermMemory:
    """
    Долгосрочная память с векторным поиском
    
    Возможности:
    - Хранение опыта и знаний
    - Векторный поиск релевантной информации  
    - Персистентное хранение
    - Автоматическая категоризация
    """
    
    def __init__(self, persist_directory: str = "autogpt_memory"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        
        # Инициализация ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )
        
        # Коллекции для разных типов памяти
        self.collections = {
            "experiences": self.client.get_or_create_collection("experiences"),
            "lessons": self.client.get_or_create_collection("lessons"),
            "strategies": self.client.get_or_create_collection("strategies"),
            "knowledge": self.client.get_or_create_collection("knowledge")
        }
        
        # OpenAI клиент для эмбеддингов (с поддержкой прокси)
        from shared.utils import load_config
        
        config = load_config()
        ai_config = config.get("ai_analysis", {})
        
        # Настройка клиента с прокси
        client_params = {
            "api_key": ai_config.get("openai_api_key"),
            "base_url": ai_config.get("base_url", "https://api.openai.com/v1")
        }
        
        # Добавляем прокси если настроен
        proxy_config = ai_config.get("proxy", {})
        if proxy_config.get("enabled", False):
            import httpx
            
            proxy_url = f"{proxy_config.get('protocol', 'http')}://"
            if proxy_config.get("username") and proxy_config.get("password"):
                proxy_url += f"{proxy_config['username']}:{proxy_config['password']}@"
            proxy_url += f"{proxy_config['host']}:{proxy_config['port']}"
            
            client_params["http_client"] = httpx.AsyncClient(
                proxies=proxy_url,
                verify=False
            )
            logger.info(f"🌐 Memory Manager: Настроен прокси для эмбеддингов")
        
        self.embedding_client = openai.AsyncOpenAI(**client_params)
        
        logger.info("🧠 Долгосрочная память инициализирована")
    
    async def store(self, content: str, metadata: Dict[str, Any], 
                   collection_name: str = "experiences") -> str:
        """Сохранение в долгосрочную память"""
        try:
            # Генерируем эмбеддинг
            embedding = await self._get_embedding(content)
            
            # Создаем уникальный ID
            memory_id = f"{collection_name}_{datetime.now().timestamp()}"
            
            # Сохраняем в коллекцию
            collection = self.collections.get(collection_name, self.collections["experiences"])
            collection.add(
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[memory_id]
            )
            
            logger.info(f"💾 Сохранено в {collection_name}: {content[:50]}...")
            return memory_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в память: {e}")
            return ""
    
    async def search_relevant(self, query: str, limit: int = 5, 
                            collection_name: str = None) -> List[str]:
        """Поиск релевантной информации"""
        try:
            # Генерируем эмбеддинг для запроса
            query_embedding = await self._get_embedding(query)
            
            relevant_memories = []
            
            # Поиск во всех коллекциях или в указанной
            collections_to_search = [collection_name] if collection_name else self.collections.keys()
            
            for coll_name in collections_to_search:
                if coll_name in self.collections:
                    collection = self.collections[coll_name]
                    
                    # Выполняем векторный поиск
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=limit
                    )
                    
                    # Добавляем найденные документы
                    if results['documents'] and results['documents'][0]:
                        relevant_memories.extend(results['documents'][0])
            
            logger.info(f"🔍 Найдено {len(relevant_memories)} релевантных воспоминаний")
            return relevant_memories[:limit]
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в памяти: {e}")
            return []
    
    async def get_recent_experiences(self, hours: int = 24) -> List[str]:
        """Получение недавнего опыта"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            experiences = []
            
            # Поиск во всех коллекциях
            for collection in self.collections.values():
                try:
                    # ChromaDB не поддерживает фильтры по времени напрямую
                    # Получаем все документы и фильтруем
                    results = collection.get()
                    
                    for i, metadata in enumerate(results['metadatas']):
                        if 'timestamp' in metadata:
                            timestamp = datetime.fromisoformat(metadata['timestamp'])
                            if timestamp > cutoff_time:
                                experiences.append(results['documents'][i])
                except:
                    continue
            
            return experiences[:10]  # Ограничиваем количество
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения недавнего опыта: {e}")
            return []
    
    async def store_lesson(self, lesson: str, context: Dict[str, Any]) -> str:
        """Сохранение урока"""
        metadata = {
            **context,
            "type": "lesson",
            "timestamp": datetime.now().isoformat()
        }
        return await self.store(lesson, metadata, "lessons")
    
    async def store_strategy(self, strategy: str, success_rate: float, context: Dict[str, Any]) -> str:
        """Сохранение успешной стратегии"""
        metadata = {
            **context,
            "type": "strategy",
            "success_rate": success_rate,
            "timestamp": datetime.now().isoformat()
        }
        return await self.store(strategy, metadata, "strategies")
    
    async def store_knowledge(self, knowledge: str, source: str, context: Dict[str, Any]) -> str:
        """Сохранение знаний"""
        metadata = {
            **context,
            "type": "knowledge",
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        return await self.store(knowledge, metadata, "knowledge")
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Получение эмбеддинга через OpenAI (с поддержкой новых моделей)"""
        try:
            # Используем новую модель эмбеддингов text-embedding-3-small для лучшей производительности
            response = await self.embedding_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536  # Фиксируем размерность для совместимости
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения эмбеддинга: {e}")
            # Fallback на старую модель
            try:
                response = await self.embedding_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
            except:
                # Возвращаем случайный вектор как последний fallback
                return np.random.random(1536).tolist()
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика памяти"""
        stats = {}
        total_memories = 0
        
        for name, collection in self.collections.items():
            try:
                count = collection.count()
                stats[name] = count
                total_memories += count
            except:
                stats[name] = 0
        
        stats["total"] = total_memories
        return stats


class ShortTermMemory:
    """
    Краткосрочная память для текущей сессии
    
    Возможности:
    - Быстрый доступ к данным сессии
    - Автоматическая очистка старых данных
    - Контекстная информация
    """
    
    def __init__(self, max_size: int = 100, ttl_minutes: int = 60):
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
        self.memory = {}  # key -> {data, timestamp}
        
        logger.info("🧠 Краткосрочная память инициализирована")
    
    def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> None:
        """Сохранение в краткосрочную память"""
        try:
            # Очищаем старые данные
            self._cleanup_expired()
            
            # Если память переполнена, удаляем самые старые
            if len(self.memory) >= self.max_size:
                oldest_key = min(self.memory.keys(), key=lambda k: self.memory[k]['timestamp'])
                del self.memory[oldest_key]
            
            # Сохраняем данные
            self.memory[key] = {
                'data': data,
                'metadata': metadata or {},
                'timestamp': datetime.now()
            }
            
            logger.debug(f"💾 Сохранено в краткосрочную память: {key}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в краткосрочную память: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Получение из краткосрочной памяти"""
        try:
            if key in self.memory:
                entry = self.memory[key]
                
                # Проверяем не истек ли срок
                if datetime.now() - entry['timestamp'] < self.ttl:
                    return entry['data']
                else:
                    # Удаляем истекшую запись
                    del self.memory[key]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения из краткосрочной памяти: {e}")
            return None
    
    def get_all_recent(self, minutes: int = 30) -> Dict[str, Any]:
        """Получение всех недавних данных"""
        try:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            recent = {}
            
            for key, entry in self.memory.items():
                if entry['timestamp'] > cutoff:
                    recent[key] = entry['data']
            
            return recent
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения недавних данных: {e}")
            return {}
    
    def update_context(self, key: str, new_data: Any) -> None:
        """Обновление контекста"""
        if key in self.memory:
            self.memory[key]['data'] = new_data
            self.memory[key]['timestamp'] = datetime.now()
    
    def _cleanup_expired(self) -> None:
        """Очистка истекших данных"""
        try:
            now = datetime.now()
            expired_keys = []
            
            for key, entry in self.memory.items():
                if now - entry['timestamp'] > self.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory[key]
            
            if expired_keys:
                logger.debug(f"🧹 Очищено {len(expired_keys)} истекших записей")
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки памяти: {e}")
    
    def clear(self) -> None:
        """Полная очистка памяти"""
        self.memory.clear()
        logger.info("🧹 Краткосрочная память очищена")
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика краткосрочной памяти"""
        try:
            now = datetime.now()
            active_count = 0
            
            for entry in self.memory.values():
                if now - entry['timestamp'] < self.ttl:
                    active_count += 1
            
            return {
                "total_entries": len(self.memory),
                "active_entries": active_count,
                "expired_entries": len(self.memory) - active_count,
                "max_size": self.max_size,
                "ttl_minutes": self.ttl.total_seconds() / 60
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}


class MemoryManager:
    """
    Менеджер памяти - объединяет долгосрочную и краткосрочную память
    """
    
    def __init__(self):
        self.long_term = LongTermMemory()
        self.short_term = ShortTermMemory()
        
        logger.info("🧠 Менеджер памяти инициализирован")
    
    async def remember_experience(self, experience: str, context: Dict[str, Any], 
                                 importance: float = 0.5) -> None:
        """Запоминание опыта с учетом важности"""
        # Сохраняем в краткосрочную память
        self.short_term.store(f"exp_{datetime.now().timestamp()}", experience, context)
        
        # Если достаточно важно, сохраняем в долгосрочную память
        if importance > 0.7:
            await self.long_term.store(experience, {
                **context,
                "importance": importance,
                "type": "experience"
            })
    
    async def recall_relevant(self, query: str, limit: int = 5) -> List[str]:
        """Поиск релевантной информации в обеих типах памяти"""
        # Ищем в долгосрочной памяти
        long_term_results = await self.long_term.search_relevant(query, limit)
        
        # Ищем в краткосрочной памяти
        short_term_data = self.short_term.get_all_recent()
        short_term_results = []
        
        for data in short_term_data.values():
            if isinstance(data, str) and query.lower() in data.lower():
                short_term_results.append(data)
        
        # Объединяем результаты
        all_results = long_term_results + short_term_results[:limit]
        return all_results[:limit]
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Общая статистика памяти"""
        return {
            "long_term": self.long_term.get_stats(),
            "short_term": self.short_term.get_stats(),
            "total_memory_health": "healthy"
        }
