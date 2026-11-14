"""
Master Memory Manager - Master Agent Memory Management

Manages long-term and short-term memory, vector search,
Learning from experience and the preservation of successful strategies.

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
    Memory Manager of Master Agent
    
    Functions:
    - Long-term memory via ChromaDB
    - Short term memory (session))
    - A vector search for similar challenges.
    - Maintaining successful strategies
    - Learning from experience
    - Analytics and metrics
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger
        
        # Configuration of memory
        self.memory_config = config.get("master_agent", {}).get("memory", {})
        
        # ChromaDB for long-term memory
        self.chroma_client = None
        self.chroma_collection = None
        
        # OpenAI for embeddings
        self.embedding_client = None
        
        # Short-term memory (in memory))
        self.short_term_memory: Dict[str, Any] = {}
        self.conversation_memory: Dict[str, List[ConversationMessage]] = {}
        self.task_memory: Dict[str, Dict[str, Any]] = {}
        
        # Cash embeddings
        self.embedding_cache: Dict[str, np.ndarray] = {}
        
        # Files for Persistence
        self.memory_dir = Path("data/master_memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_file = self.memory_dir / "sessions.json"
        self.strategies_file = self.memory_dir / "successful_strategies.json"
        self.metrics_file = self.memory_dir / "quality_metrics.json"
        
        # Statistics
        self.stats = {
            "embeddings_created": 0,
            "similarity_searches": 0,
            "strategies_saved": 0,
            "cache_hits": 0,
            "memory_operations": 0
        }
    
    async def initialize(self):
        'Initialization of Memory Manager'
        try:
            # Initialization of ChromaDB
            await self._initialize_chromadb()
            
            # Initialization of OpenAI for embeddings
            await self._initialize_embedding_client()
            
            # Loading the stored memory
            await self._load_persistent_memory()
            
            self.logger.info('✅ Master Memory Manager initialized')
            
        except Exception as e:
            self.logger.error(f"Error: ❌ The Master Memory Manager: {e}")
            raise
    
    async def _initialize_chromadb(self):
        'Initialization of ChromaDB'
        try:
            # Path to ChromaDB database
            chroma_path = self.memory_dir / "chroma_db"
            chroma_path.mkdir(exist_ok=True)
            
            # Creating a ChromaDB client
            self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
            
            # Create or receive collection
            collection_name = "master_agent_memory"
            try:
                self.chroma_collection = self.chroma_client.get_collection(collection_name)
                self.logger.info(f"✅ ChromaDB Collection upload: {collection_name}")
            except:
                self.chroma_collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "Master Agent long-term memory"}
                )
                self.logger.info(f"✅ ChromaDB Collection Created: {collection_name}")
            
        except Exception as e:
            self.logger.error(f"❌ Initialization errors of ChromaDB: {e}")
            raise
    
    async def _initialize_embedding_client(self):
        'Customer Initialization for Embeddings'
        try:
            ai_config = self.config.get("master_agent", {})
            
            # Settings of Proxi
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
            
            # OpenRouter or OpenAI client for embeddings
            base_url = ai_config.get("base_url", "https://openrouter.ai/api/v1")
            api_key = ai_config.get("openrouter_api_key") or ai_config.get("openai_api_key")
            
            self.embedding_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )
            
            self.logger.info('✅ Embedding client initialized')
            
        except Exception as e:
            self.logger.error(f"❌ Initialization error of customer embedding: {e}")
            raise
    
    async def save_task_experience(self, task_data: Dict[str, Any], result: Dict[str, Any]):
        'Keeping the experience of performing a task in long-term memory'
        try:
            # Preparation of data for preservation
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
            
            # Create text for embedding
            experience_text = self._create_experience_text(experience)
            
            # Getting embedding
            embedding = await self._get_embedding(experience_text)
            
            # Saved at ChromaDB
            experience_id = f"exp_{uuid.uuid4().hex[:8]}"
            
            self.chroma_collection.add(
                ids=[experience_id],
                documents=[experience_text],
                embeddings=[embedding.tolist()],
                metadatas=[experience]
            )
            
            self.stats["memory_operations"] += 1
            self.logger.info(f"✅ The experience of the task is retained: {experience_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error inining experience: {e}")
    
    async def find_similar_tasks(self, goal: str, limit: int = 5) -> List[Dict[str, Any]]:
        'Search for similar tasks in memory'
        try:
            if not self.chroma_collection:
                return []
            
            # Getting embedding for purpose
            goal_embedding = await self._get_embedding(goal)
            
            # Finding Similar Challenges
            results = self.chroma_collection.query(
                query_embeddings=[goal_embedding.tolist()],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            similar_tasks = []
            if results["metadatas"] and len(results["metadatas"]) > 0:
                for i, metadata in enumerate(results["metadatas"][0]):
                    similarity = 1 - results["distances"][0][i]  # Convergence of distance
                    
                    if similarity > 0.7:  # The threshold of similarity
                        similar_tasks.append({
                            "experience": metadata,
                            "similarity": similarity,
                            "document": results["documents"][0][i] if results["documents"] else ""
                        })
            
            self.stats["similarity_searches"] += 1
            self.logger.info(f"✅ Found {len(similar_tasks)} Similar tasks")
            
            return similar_tasks
            
        except Exception as e:
            self.logger.error(f"❌ Error in finding similar tasks: {e}")
            return []
    
    async def save_successful_strategy(self, strategy: Dict[str, Any]):
        'Maintaining a successful strategy'
        try:
            strategy_id = f"strategy_{uuid.uuid4().hex[:8]}"
            strategy["id"] = strategy_id
            strategy["timestamp"] = datetime.now().isoformat()
            
            # Uploading of existing strategies
            strategies = []
            if self.strategies_file.exists():
                with open(self.strategies_file, 'r', encoding='utf-8') as f:
                    strategies = json.load(f)
            
            # Adding a new strategy
            strategies.append(strategy)
            
            # Limiting the number of strategies (last 100)
            if len(strategies) > 100:
                strategies = strategies[-100:]
            
            # Saving
            with open(self.strategies_file, 'w', encoding='utf-8') as f:
                json.dump(strategies, f, ensure_ascii=False, indent=2)
            
            # Also stored in vector base
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
            self.logger.info(f"✅ Successful strategy maintained: {strategy_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Mistake of Strategy Maintenance: {e}")
    
    async def get_master_memory(self) -> Optional[MasterMemory]:
        'Acquisition of the main memory of the master agent'
        try:
            # Recovery from short-term memory
            memory = MasterMemory(
                conversation_history=list(self.conversation_memory.values()),
                active_tasks=self.task_memory,
                organization_context=None,  # To be downloaded from OrganizationContextManager
                learned_patterns=self.short_term_memory.get("learned_patterns", {}),
                successful_strategies=await self._load_successful_strategies()
            )
            
            return memory
            
        except Exception as e:
            self.logger.error(f"❌ Error of Memory: {e}")
            return None
    
    async def save_conversation(self, conversation_id: str, messages: List[ConversationMessage]):
        'Keeping the dialogue in memory'
        try:
            self.conversation_memory[conversation_id] = messages
            
            # Keeping dialogue in long-term memory
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
            self.logger.info(f"✅ Dialogue maintained: {conversation_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Mistake of dialogue: {e}")
    
    async def save_quality_metrics(self, metrics: QualityMetrics):
        'Maintaining quality metrics'
        try:
            # Loading of existing metrics
            all_metrics = []
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    all_metrics = json.load(f)
            
            # Adding new metrics
            all_metrics.append(metrics.dict())
            
            # Quantity limitation (last 1,000 entries)
            if len(all_metrics) > 1000:
                all_metrics = all_metrics[-1000:]
            
            # Saving
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(all_metrics, f, ensure_ascii=False, indent=2)
            
            self.stats["memory_operations"] += 1
            self.logger.info(f"✅ Quality metrics maintained: {metrics.task_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error of preservation of metric: {e}")
    
    async def learn_from_feedback(self, task_id: str, feedback: Dict[str, Any]):
        'Feedback-based training'
        try:
            # Search for related experience
            task_experiences = self.chroma_collection.query(
                where={"task_id": task_id},
                n_results=10
            )
            
            if task_experiences["metadatas"]:
                # Update patterns based on Feedback
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
                
                self.logger.info(f"✅ Feedback training for the task {task_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Feedback Learning Error: {e}")
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        'Compute the text embedding'
        try:
            # Cash check
            text_hash = str(hash(text))
            if text_hash in self.embedding_cache:
                self.stats["cache_hits"] += 1
                return self.embedding_cache[text_hash]
            
            # Creating Embedding through OpenAI
            response = await self.embedding_client.embeddings.create(
                model="text-embedding-3-small",  # A Newer Model
                input=text
            )
            
            embedding = np.array(response.data[0].embedding)
            
            # Saved in Cash
            self.embedding_cache[text_hash] = embedding
            
            self.stats["embeddings_created"] += 1
            return embedding
            
        except Exception as e:
            # Fallback in case of error
            self.logger.warning(f"⚠️ The error of embedding: {e}, random vector used")
            return np.random.rand(1536)  # Embedding size for text-embedding-3-small
    
    def _create_experience_text(self, experience: Dict[str, Any]) -> str:
        'Create text for embedding experiences'
        return f"""
Task: {experience.get('goal', '')}
Type: {experience.get('task_type', '')}
Complexity: {experience.get('complexity', '')}
Agents: {', '.join(experience.get('agents_used', []))}
Result: {'success' if experience.get('success') else 'failed'}
Quality: {experience.get('quality_score', 0)}
Lessons: {', '.join(experience.get('lessons_learned', []))}
""".strip()
    
    def _create_strategy_text(self, strategy: Dict[str, Any]) -> str:
        'Create text for embedding strategy'
        return f"""
Target Pattern: {strategy.get('goal_pattern', '')}
Analysis: {json.dumps(strategy.get('analysis', {}), ensure_ascii=False)}
Plan: {json.dumps(strategy.get('plan', {}), ensure_ascii=False)}
Success: {strategy.get('success_metrics', {})}
""".strip()
    
    def _create_conversation_text(self, messages: List[ConversationMessage]) -> str:
        'Build text for the conversation embedding'
        conversation_parts = []
        for msg in messages[-10:]:  # Last 10 communications
            conversation_parts.append(f"{msg.sender}: {msg.content}")
        
        return "\n".join(conversation_parts)
    
    async def _load_persistent_memory(self):
        'Loading the stored memory'
        try:
            # Loading of sessions
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    self.short_term_memory.update(session_data)
                    self.logger.info('✅ Session memory charged')
            
        except Exception as e:
            self.logger.error(f"❌ Error of recording memory: {e}")
    
    async def _load_successful_strategies(self) -> List[Dict[str, Any]]:
        'Uploading successful strategies'
        try:
            if self.strategies_file.exists():
                with open(self.strategies_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"❌ Errors in Strategic Loading: {e}")
            return []
    
    async def cleanup_old_memory(self, days_old: int = 30):
        'Cleaning of Old Memory'
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Cleaning of Old Conversations
            old_conv_ids = []
            for conv_id, messages in self.conversation_memory.items():
                if messages and messages[-1].timestamp < cutoff_date:
                    old_conv_ids.append(conv_id)
            
            for conv_id in old_conv_ids:
                del self.conversation_memory[conv_id]
            
            self.logger.info(f"✅ Peeled {len(old_conv_ids)} old dialogues")
            
        except Exception as e:
            self.logger.error(f"❌ Error of memory cleaning: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        'Obtaining memory statistics'
        try:
            # ChromaDB statistics
            chroma_stats = {}
            if self.chroma_collection:
                try:
                    chroma_stats = {
                        "total_documents": self.chroma_collection.count(),
                        "collection_name": self.chroma_collection.name
                    }
                except:
                    chroma_stats = {"error": 'Unable to obtain ChromaDB statistics'}
            
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
            self.logger.error(f"❌ Error in obtaining memory statistics: {e}")
            return {"error": str(e)}
    
    async def save_session(self):
        'Save the current session'
        try:
            session_data = {
                "short_term_memory": self.short_term_memory,
                "last_save": datetime.now().isoformat()
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info('✅ Session retained')
            
        except Exception as e:
            self.logger.error(f"❌ Mistake of Session: {e}")
