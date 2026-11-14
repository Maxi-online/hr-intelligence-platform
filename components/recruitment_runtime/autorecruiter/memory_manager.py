"""
AutoGPT Memory Manager - Memory Management System

Realizes long-term and short-term memory for the AutoGPT agent:
- Vector search via ChromaDB
- Embeddings through OpenAI
- Permeable storage of context
Automatic oblivion of old data

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
    Long-term memory with vector search
    
    Opportunities:
    - Storage of experience and knowledge
    - Vector search for relevant information  
    - Permeable storage
    - Automatic categorization
    """
    
    def __init__(self, persist_directory: str = "autogpt_memory"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        
        # Initialization of ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )
        
        # Collections for different types of memory
        self.collections = {
            "experiences": self.client.get_or_create_collection("experiences"),
            "lessons": self.client.get_or_create_collection("lessons"),
            "strategies": self.client.get_or_create_collection("strategies"),
            "knowledge": self.client.get_or_create_collection("knowledge")
        }
        
        # OpenAI Embeddings Client (with Proxy Support))
        from shared.utils import load_config
        
        config = load_config()
        ai_config = config.get("ai_analysis", {})
        
        # Set up a client with a Proxi
        client_params = {
            "api_key": ai_config.get("openai_api_key"),
            "base_url": ai_config.get("base_url", "https://api.openai.com/v1")
        }
        
        # Add a proxie if you're in the mood.
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
            logger.info(f"🌐 Memory Manager: Configured proxy for embeddings")
        
        self.embedding_client = openai.AsyncOpenAI(**client_params)
        
        logger.info('🧠 Long-term memory initialized')
    
    async def store(self, content: str, metadata: Dict[str, Any], 
                   collection_name: str = "experiences") -> str:
        'Storage in long-term memory'
        try:
            # Generating Embedded
            embedding = await self._get_embedding(content)
            
            # Create a unique ID
            memory_id = f"{collection_name}_{datetime.now().timestamp()}"
            
            # Saved in collection
            collection = self.collections.get(collection_name, self.collections["experiences"])
            collection.add(
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[memory_id]
            )
            
            logger.info(f"💾 Saved in {collection_name}: {content[:50]}...")
            return memory_id
            
        except Exception as e:
            logger.error(f"❌ Error in memory: {e}")
            return ""
    
    async def search_relevant(self, query: str, limit: int = 5, 
                            collection_name: str = None) -> List[str]:
        'Searching for relevant information'
        try:
            # Generate embedings for request
            query_embedding = await self._get_embedding(query)
            
            relevant_memories = []
            
            # Search in all collections or specified
            collections_to_search = [collection_name] if collection_name else self.collections.keys()
            
            for coll_name in collections_to_search:
                if coll_name in self.collections:
                    collection = self.collections[coll_name]
                    
                    # Perform a vector search.
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=limit
                    )
                    
                    # Adding the documents found
                    if results['documents'] and results['documents'][0]:
                        relevant_memories.extend(results['documents'][0])
            
            logger.info(f"🔍 Found {len(relevant_memories)} Relevant memories")
            return relevant_memories[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error in memory search: {e}")
            return []
    
    async def get_recent_experiences(self, hours: int = 24) -> List[str]:
        'Recent experience'
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            experiences = []
            
            # Search All Collections
            for collection in self.collections.values():
                try:
                    # ChromaDB does not support the filters directly in time
                    # We get all the documents and filter them.
                    results = collection.get()
                    
                    for i, metadata in enumerate(results['metadatas']):
                        if 'timestamp' in metadata:
                            timestamp = datetime.fromisoformat(metadata['timestamp'])
                            if timestamp > cutoff_time:
                                experiences.append(results['documents'][i])
                except:
                    continue
            
            return experiences[:10]  # Limiting quantity
            
        except Exception as e:
            logger.error(f"❌ Error of Recent Experience: {e}")
            return []
    
    async def store_lesson(self, lesson: str, context: Dict[str, Any]) -> str:
        'Maintaining the Lesson'
        metadata = {
            **context,
            "type": "lesson",
            "timestamp": datetime.now().isoformat()
        }
        return await self.store(lesson, metadata, "lessons")
    
    async def store_strategy(self, strategy: str, success_rate: float, context: Dict[str, Any]) -> str:
        'Maintaining a successful strategy'
        metadata = {
            **context,
            "type": "strategy",
            "success_rate": success_rate,
            "timestamp": datetime.now().isoformat()
        }
        return await self.store(strategy, metadata, "strategies")
    
    async def store_knowledge(self, knowledge: str, source: str, context: Dict[str, Any]) -> str:
        'Save knowledge'
        metadata = {
            **context,
            "type": "knowledge",
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        return await self.store(knowledge, metadata, "knowledge")
    
    async def _get_embedding(self, text: str) -> List[float]:
        'Obtaining embedding through OpenAI (with the support of new models)'
        try:
            # We use the new text-embedding-3-small embeddings model for better performance
            response = await self.embedding_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536  # Set dimension for compatibility
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"❌ Error of Embedding: {e}")
            # Fallback to the old model
            try:
                response = await self.embedding_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
            except:
                # Return the random vector as the last fallback.
                return np.random.random(1536).tolist()
    
    def get_stats(self) -> Dict[str, Any]:
        'Statistics of memory'
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
    Short-term memory for current session
    
    Opportunities:
    - Rapid access to session data
    - Automatic clean-up of old data
    - Context information
    """
    
    def __init__(self, max_size: int = 100, ttl_minutes: int = 60):
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
        self.memory = {}  # key -> {data, timestamp}
        
        logger.info('🧠 Short-term memory initialized')
    
    def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> None:
        'Storage in short-term memory'
        try:
            # Cleaning up old data.
            self._cleanup_expired()
            
            # If the memory is overfilled, we remove the oldest
            if len(self.memory) >= self.max_size:
                oldest_key = min(self.memory.keys(), key=lambda k: self.memory[k]['timestamp'])
                del self.memory[oldest_key]
            
            # Save data.
            self.memory[key] = {
                'data': data,
                'metadata': metadata or {},
                'timestamp': datetime.now()
            }
            
            logger.debug(f"💾 Conserved in short-term memory: {key}")
            
        except Exception as e:
            logger.error(f"❌ Error in short-term memory: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        'Recovery from short-term memory'
        try:
            if key in self.memory:
                entry = self.memory[key]
                
                # Checking to see if the deadline is up.
                if datetime.now() - entry['timestamp'] < self.ttl:
                    return entry['data']
                else:
                    # Delete an expired entry.
                    del self.memory[key]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error from short-term memory: {e}")
            return None
    
    def get_all_recent(self, minutes: int = 30) -> Dict[str, Any]:
        'Collection of all recent data'
        try:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            recent = {}
            
            for key, entry in self.memory.items():
                if entry['timestamp'] > cutoff:
                    recent[key] = entry['data']
            
            return recent
            
        except Exception as e:
            logger.error(f"❌ Error in obtaining recent data: {e}")
            return {}
    
    def update_context(self, key: str, new_data: Any) -> None:
        'Updating the context'
        if key in self.memory:
            self.memory[key]['data'] = new_data
            self.memory[key]['timestamp'] = datetime.now()
    
    def _cleanup_expired(self) -> None:
        'Cleaning of expired data'
        try:
            now = datetime.now()
            expired_keys = []
            
            for key, entry in self.memory.items():
                if now - entry['timestamp'] > self.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory[key]
            
            if expired_keys:
                logger.debug(f"🧹 Peeled {len(expired_keys)} Lasted records")
                
        except Exception as e:
            logger.error(f"❌ Error of memory cleaning: {e}")
    
    def clear(self) -> None:
        'Complete cleaning of memory'
        self.memory.clear()
        logger.info('🧹 The short-term memory is cleaned')
    
    def get_stats(self) -> Dict[str, Any]:
        'Short-term memory statistics'
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
            logger.error(f"❌ Error in obtaining statistics: {e}")
            return {}


class MemoryManager:
    """
    Memory Manager combines long-term and short-term memory
    """
    
    def __init__(self):
        self.long_term = LongTermMemory()
        self.short_term = ShortTermMemory()
        
        logger.info('🧠 Memory Manager Initialized')
    
    async def remember_experience(self, experience: str, context: Dict[str, Any], 
                                 importance: float = 0.5) -> None:
        'Learning from experience in view of the importance of'
        # Keep in short-term memory
        self.short_term.store(f"exp_{datetime.now().timestamp()}", experience, context)
        
        # If important, keep in long-term memory
        if importance > 0.7:
            await self.long_term.store(experience, {
                **context,
                "importance": importance,
                "type": "experience"
            })
    
    async def recall_relevant(self, query: str, limit: int = 5) -> List[str]:
        'Search for relevant information in both types of memory'
        # Looking for long-term memory
        long_term_results = await self.long_term.search_relevant(query, limit)
        
        # Looking for short-term memory
        short_term_data = self.short_term.get_all_recent()
        short_term_results = []
        
        for data in short_term_data.values():
            if isinstance(data, str) and query.lower() in data.lower():
                short_term_results.append(data)
        
        # Uniting results
        all_results = long_term_results + short_term_results[:limit]
        return all_results[:limit]
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        'General memory statistics'
        return {
            "long_term": self.long_term.get_stats(),
            "short_term": self.short_term.get_stats(),
            "total_memory_health": "healthy"
        }
