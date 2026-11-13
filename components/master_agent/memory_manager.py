"""
Master Memory Manager - Управление памятью мастер-агента

Управляет долгосрочной и краткосрочной памятью, векторным поиском,
обучением на основе опыта и хранением успешных стратегий.

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import pickle
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import chromadb
import numpy as np
from openai import AsyncOpenAI
import httpx

from .models import MasterMemory, ConversationMessage, QualityMetrics

logger = logging.getLogger("master-memory")


class MasterMemoryManager:
    """
    Менеджер памяти мастер-агента
    
    Функции:
    - Долгосрочная память через ChromaDB
    - Краткосрочная память (сессии)
    - Векторный поиск похожих задач
    - Сохранение успешных стратегий
    - Обучение на основе опыта
    - Аналитика и метрики
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger
        
        # Конфигурация памяти
        self.memory_config = config.get("master_agent", {}).get("memory", {})
        
        # ChromaDB для долгосрочной памяти
        self.chroma_client = None
        self.chroma_collection = None
        
        # OpenAI для embeddings
        self.embedding_client = None
        
        # Краткосрочная память (в памяти)
        self.short_term_memory: Dict[str, Any] = {}
        self.conversation_memory: Dict[str, List[ConversationMessage]] = {}
        self.task_memory: Dict[str, Dict[str, Any]] = {}
        
        # Кэш embeddings
        self.embedding_cache: Dict[str, np.ndarray] = {}
        
        # Файлы для персистентности
        self.memory_dir = Path("data/master_memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_file = self.memory_dir / "sessions.json"
        self.strategies_file = self.memory_dir / "successful_strategies.json"
        self.metrics_file = self.memory_dir / "quality_metrics.json"
        
        # Статистика
        self.stats = {
            "embeddings_created": 0,
            "similarity_searches": 0,
            "strategies_saved": 0,
            "cache_hits": 0,
            "memory_operations": 0
        }
    
    async def initialize(self):
        """Инициализация менеджера памяти"""
        try:
            # Инициализация ChromaDB
            await self._initialize_chromadb()
            
            # Инициализация OpenAI для embeddings
            await self._initialize_embedding_client()
            
            # Загрузка сохраненной памяти
            await self._load_persistent_memory()
            
            self.logger.info("✅ Master Memory Manager инициализирован")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации Master Memory Manager: {e}")
            raise
    
    async def _initialize_chromadb(self):
        """Инициализация ChromaDB"""
        try:
            # Путь к базе данных ChromaDB
            chroma_path = self.memory_dir / "chroma_db"
            chroma_path.mkdir(exist_ok=True)
            
            # Создание клиента ChromaDB
            self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
            
            # Создание или получение коллекции
            collection_name = "master_agent_memory"
            try:
                self.chroma_collection = self.chroma_client.get_collection(collection_name)
                self.logger.info(f"✅ Коллекция ChromaDB загружена: {collection_name}")
            except:
                self.chroma_collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "Master Agent long-term memory"}
                )
                self.logger.info(f"✅ Коллекция ChromaDB создана: {collection_name}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации ChromaDB: {e}")
            raise
    
    async def _initialize_embedding_client(self):
        """Инициализация клиента для embeddings"""
        try:
            ai_config = self.config.get("master_agent", {})
            
            # Настройка прокси
            proxy_config = ai_config.get("proxy", {})
            proxy_enabled = proxy_config.get("enabled", False)
            
            http_client = None
            if proxy_enabled:
                proxy_host = proxy_config.get("host", "")
                proxy_port = proxy_config.get("port", "")
                if proxy_host and proxy_port:
                    proxy_url = f"http://{proxy_host}:{proxy_port}"
                    http_client = httpx.AsyncClient(proxy=proxy_url, timeout=httpx.Timeout(60.0))
            
            if not http_client:
                http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
            
            # OpenRouter или OpenAI клиент для embeddings
            base_url = ai_config.get("base_url", "https://openrouter.ai/api/v1")
            api_key = ai_config.get("openrouter_api_key") or ai_config.get("openai_api_key")
            
            self.embedding_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
            
            self.logger.info("✅ Embedding клиент инициализирован")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации embedding клиента: {e}")
            raise
    
    async def save_task_experience(self, task_data: Dict[str, Any], result: Dict[str, Any]):
        """Сохранение опыта выполнения задачи в долгосрочную память"""
        try:
            # Подготовка данных для сохранения
            experience = {
                "task_id": task_data.get("id"),
                "goal": task_data.get("request", {}).get("goal", ""),
                "task_type": task_data.get("analysis", {}).get("task_type", "unknown"),
                "complexity": task_data.get("analysis", {}).get("complexity", "medium"),
                "agents_used": task_data.get("plan", {}).get("agents", []),
                "execution_time": task_data.get("execution_time", 0),
                "success": result.get("success", False),
                "quality_score": result.get("quality_score", 0.5),
                "lessons_learned": result.get("lessons_learned", []),
                "timestamp": datetime.now().isoformat()
            }
            
            # Создание текста для embedding
            experience_text = self._create_experience_text(experience)
            
            # Получение embedding
            embedding = await self._get_embedding(experience_text)
            
            # Сохранение в ChromaDB
            experience_id = f"exp_{uuid.uuid4().hex[:8]}"
            
            self.chroma_collection.add(
                ids=[experience_id],
                documents=[experience_text],
                embeddings=[embedding.tolist()],
                metadatas=[experience]
            )
            
            self.stats["memory_operations"] += 1
            self.logger.info(f"✅ Опыт задачи сохранен: {experience_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения опыта задачи: {e}")
    
    async def find_similar_tasks(self, goal: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Поиск похожих задач в памяти"""
        try:
            if not self.chroma_collection:
                return []
            
            # Получение embedding для цели
            goal_embedding = await self._get_embedding(goal)
            
            # Поиск похожих задач
            results = self.chroma_collection.query(
                query_embeddings=[goal_embedding.tolist()],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            similar_tasks = []
            if results["metadatas"] and len(results["metadatas"]) > 0:
                for i, metadata in enumerate(results["metadatas"][0]):
                    similarity = 1 - results["distances"][0][i]  # Конвертация расстояния в схожесть
                    
                    if similarity > 0.7:  # Порог схожести
                        similar_tasks.append({
                            "experience": metadata,
                            "similarity": similarity,
                            "document": results["documents"][0][i] if results["documents"] else ""
                        })
            
            self.stats["similarity_searches"] += 1
            self.logger.info(f"✅ Найдено {len(similar_tasks)} похожих задач")
            
            return similar_tasks
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска похожих задач: {e}")
            return []
    
    async def save_successful_strategy(self, strategy: Dict[str, Any]):
        """Сохранение успешной стратегии"""
        try:
            strategy_id = f"strategy_{uuid.uuid4().hex[:8]}"
            strategy["id"] = strategy_id
            strategy["timestamp"] = datetime.now().isoformat()
            
            # Загрузка существующих стратегий
            strategies = []
            if self.strategies_file.exists():
                with open(self.strategies_file, 'r', encoding='utf-8') as f:
                    strategies = json.load(f)
            
            # Добавление новой стратегии
            strategies.append(strategy)
            
            # Ограничение количества стратегий (последние 100)
            if len(strategies) > 100:
                strategies = strategies[-100:]
            
            # Сохранение
            with open(self.strategies_file, 'w', encoding='utf-8') as f:
                json.dump(strategies, f, ensure_ascii=False, indent=2)
            
            # Также сохранение в векторную базу
            strategy_text = self._create_strategy_text(strategy)
            embedding = await self._get_embedding(strategy_text)
            
            self.chroma_collection.add(
                ids=[strategy_id],
                documents=[strategy_text],
                embeddings=[embedding.tolist()],
                metadatas={
                    "type": "strategy",
                    "success_rate": strategy.get("success_metrics", {}).get("success_rate", 1.0),
                    **strategy
                }
            )
            
            self.stats["strategies_saved"] += 1
            self.logger.info(f"✅ Успешная стратегия сохранена: {strategy_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения стратегии: {e}")
    
    async def get_master_memory(self) -> Optional[MasterMemory]:
        """Получение основной памяти мастер-агента"""
        try:
            # Восстановление из краткосрочной памяти
            memory = MasterMemory(
                conversation_history=list(self.conversation_memory.values()),
                active_tasks=self.task_memory,
                organization_context=None,  # Будет загружен из OrganizationContextManager
                learned_patterns=self.short_term_memory.get("learned_patterns", {}),
                successful_strategies=await self._load_successful_strategies()
            )
            
            return memory
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения памяти: {e}")
            return None
    
    async def save_conversation(self, conversation_id: str, messages: List[ConversationMessage]):
        """Сохранение диалога в память"""
        try:
            self.conversation_memory[conversation_id] = messages
            
            # Также сохранение диалога в долгосрочную память
            conversation_text = self._create_conversation_text(messages)
            embedding = await self._get_embedding(conversation_text)
            
            conversation_memory_id = f"conv_{conversation_id}_{uuid.uuid4().hex[:8]}"
            
            self.chroma_collection.add(
                ids=[conversation_memory_id],
                documents=[conversation_text],
                embeddings=[embedding.tolist()],
                metadatas={
                    "type": "conversation",
                    "conversation_id": conversation_id,
                    "messages_count": len(messages),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            self.stats["memory_operations"] += 1
            self.logger.info(f"✅ Диалог сохранен: {conversation_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения диалога: {e}")
    
    async def save_quality_metrics(self, metrics: QualityMetrics):
        """Сохранение метрик качества"""
        try:
            # Загрузка существующих метрик
            all_metrics = []
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    all_metrics = json.load(f)
            
            # Добавление новых метрик
            all_metrics.append(metrics.dict())
            
            # Ограничение количества (последние 1000 записей)
            if len(all_metrics) > 1000:
                all_metrics = all_metrics[-1000:]
            
            # Сохранение
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(all_metrics, f, ensure_ascii=False, indent=2)
            
            self.stats["memory_operations"] += 1
            self.logger.info(f"✅ Метрики качества сохранены: {metrics.task_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения метрик: {e}")
    
    async def learn_from_feedback(self, task_id: str, feedback: Dict[str, Any]):
        """Обучение на основе обратной связи"""
        try:
            # Поиск связанного опыта
            task_experiences = self.chroma_collection.query(
                where={"task_id": task_id},
                n_results=10
            )
            
            if task_experiences["metadatas"]:
                # Обновление patterns на основе feedback
                patterns = self.short_term_memory.get("learned_patterns", {})
                
                feedback_type = feedback.get("type", "general")
                if feedback_type not in patterns:
                    patterns[feedback_type] = []
                
                patterns[feedback_type].append({
                    "task_id": task_id,
                    "feedback": feedback,
                    "timestamp": datetime.now().isoformat()
                })
                
                self.short_term_memory["learned_patterns"] = patterns
                
                self.logger.info(f"✅ Обучение на основе feedback для задачи {task_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обучения на feedback: {e}")
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Получение embedding для текста"""
        try:
            # Проверка кэша
            text_hash = str(hash(text))
            if text_hash in self.embedding_cache:
                self.stats["cache_hits"] += 1
                return self.embedding_cache[text_hash]
            
            # Создание embedding через OpenAI
            response = await self.embedding_client.embeddings.create(
                model="text-embedding-3-small",  # Более новая модель
                input=text
            )
            
            embedding = np.array(response.data[0].embedding)
            
            # Сохранение в кэш
            self.embedding_cache[text_hash] = embedding
            
            self.stats["embeddings_created"] += 1
            return embedding
            
        except Exception as e:
            # Fallback на случай ошибки
            self.logger.warning(f"⚠️ Ошибка создания embedding: {e}, используется случайный вектор")
            return np.random.rand(1536)  # Размер embedding для text-embedding-3-small
    
    def _create_experience_text(self, experience: Dict[str, Any]) -> str:
        """Создание текста для embedding опыта"""
        return f"""
Задача: {experience.get('goal', '')}
Тип: {experience.get('task_type', '')}
Сложность: {experience.get('complexity', '')}
Агенты: {', '.join(experience.get('agents_used', []))}
Результат: {'успех' if experience.get('success') else 'неуспех'}
Качество: {experience.get('quality_score', 0)}
Уроки: {', '.join(experience.get('lessons_learned', []))}
""".strip()
    
    def _create_strategy_text(self, strategy: Dict[str, Any]) -> str:
        """Создание текста для embedding стратегии"""
        return f"""
Паттерн цели: {strategy.get('goal_pattern', '')}
Анализ: {json.dumps(strategy.get('analysis', {}), ensure_ascii=False)}
План: {json.dumps(strategy.get('plan', {}), ensure_ascii=False)}
Успешность: {strategy.get('success_metrics', {})}
""".strip()
    
    def _create_conversation_text(self, messages: List[ConversationMessage]) -> str:
        """Создание текста для embedding диалога"""
        conversation_parts = []
        for msg in messages[-10:]:  # Последние 10 сообщений
            conversation_parts.append(f"{msg.sender}: {msg.content}")
        
        return "\n".join(conversation_parts)
    
    async def _load_persistent_memory(self):
        """Загрузка сохраненной памяти"""
        try:
            # Загрузка сессий
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    self.short_term_memory.update(session_data)
                    self.logger.info("✅ Сессионная память загружена")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки сохраненной памяти: {e}")
    
    async def _load_successful_strategies(self) -> List[Dict[str, Any]]:
        """Загрузка успешных стратегий"""
        try:
            if self.strategies_file.exists():
                with open(self.strategies_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки стратегий: {e}")
            return []
    
    async def cleanup_old_memory(self, days_old: int = 30):
        """Очистка старой памяти"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Очистка старых conversations
            old_conv_ids = []
            for conv_id, messages in self.conversation_memory.items():
                if messages and messages[-1].timestamp < cutoff_date:
                    old_conv_ids.append(conv_id)
            
            for conv_id in old_conv_ids:
                del self.conversation_memory[conv_id]
            
            self.logger.info(f"✅ Очищено {len(old_conv_ids)} старых диалогов")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка очистки памяти: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики памяти"""
        try:
            # Статистика ChromaDB
            chroma_stats = {}
            if self.chroma_collection:
                try:
                    chroma_stats = {
                        "total_documents": self.chroma_collection.count(),
                        "collection_name": self.chroma_collection.name
                    }
                except:
                    chroma_stats = {"error": "Не удалось получить статистику ChromaDB"}
            
            return {
                "stats": self.stats,
                "short_term_memory_size": len(self.short_term_memory),
                "conversations_count": len(self.conversation_memory),
                "task_memory_count": len(self.task_memory),
                "embedding_cache_size": len(self.embedding_cache),
                "chroma_stats": chroma_stats,
                "memory_files": {
                    "session_file_exists": self.session_file.exists(),
                    "strategies_file_exists": self.strategies_file.exists(),
                    "metrics_file_exists": self.metrics_file.exists()
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статистики памяти: {e}")
            return {"error": str(e)}
    
    async def save_session(self):
        """Сохранение текущей сессии"""
        try:
            session_data = {
                "short_term_memory": self.short_term_memory,
                "last_save": datetime.now().isoformat()
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info("✅ Сессия сохранена")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения сессии: {e}")
