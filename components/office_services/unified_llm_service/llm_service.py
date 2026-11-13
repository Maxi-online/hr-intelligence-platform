"""
Единый LLM микросервис GPT-5
Получает информацию из SQL для ответа того или иного агента и имитирует ответ агента
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from openai import AsyncOpenAI
import httpx
import psycopg2
import json

logger = logging.getLogger(__name__)

class UnifiedLLMService:
    """Единый LLM микросервис для всех агентов"""
    
    def __init__(self, openai_config: Dict[str, Any], db_config: Dict[str, Any]):
        self.openai_config = openai_config
        self.db_config = db_config
        self.db_connection = None
        
        # Инициализация OpenAI клиента с прокси
        self._init_openai_client()
        
        logger.info("🤖 Unified LLM Service инициализирован")
    
    def _init_openai_client(self):
        """Инициализация OpenAI клиента с прокси"""
        proxy_url = self.openai_config.get('proxy_url')
        
        if proxy_url:
            logger.info(f"🔧 Настройка OpenAI с прокси: {proxy_url}")
            
            http_client = httpx.AsyncClient(
                proxy=proxy_url,
                timeout=30.0
            )
            
            self.openai_client = AsyncOpenAI(
                api_key=self.openai_config['api_key'],
                http_client=http_client
            )
            logger.info("✅ OpenAI клиент настроен с прокси")
        else:
            raise ValueError("Прокси ОБЯЗАТЕЛЕН! Добавьте proxy_url в конфигурацию")
    
    async def initialize(self):
        """Инициализация сервиса"""
        await self._connect_to_database()
        logger.info("✅ Unified LLM Service готов к работе")
    
    async def _connect_to_database(self):
        """Подключение к централизованной PostgreSQL базе данных"""
        try:
            self.db_connection = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database']
            )
            logger.info("✅ Подключение к централизованной PostgreSQL базе данных установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            raise
    
    async def generate_agent_response(self, agent_id: str, user_message: str, 
                                    user_id: str, session_id: str = None) -> str:
        """
        Генерация ответа агента на основе его конфигурации из SQL
        
        Args:
            agent_id: ID агента (boss_ai, alena_ai, sergei_ai)
            user_message: Входящее сообщение пользователя
            user_id: ID пользователя
            session_id: ID сессии (опционально)
            
        Returns:
            str: Ответ агента
        """
        logger.info(f"🎯 Генерация ответа агента {agent_id} для пользователя {user_id}")
        
        try:
            # 1. Получаем конфигурацию агента из SQL
            agent_config = await self._get_agent_configuration(agent_id)
            if not agent_config:
                return f"❌ Агент {agent_id} не найден в базе данных"
            
            # 2. Получаем оперативную память (контекст задач)
            operational_memory = await self._get_operational_memory(agent_id, user_id, session_id)
            
            # 3. Получаем core-память (правила)
            core_memory = await self._get_core_memory(agent_id)
            
            # 4. Получаем историю чата
            chat_history = await self._get_chat_history(agent_id, user_id, session_id)
            
            # 5. Формируем системный промпт с персонализацией
            system_prompt = self._build_system_prompt(agent_config, operational_memory, core_memory)
            
            # 6. Формируем сообщения для GPT
            messages = self._build_messages(system_prompt, chat_history, user_message)
            
            # 7. Генерируем ответ через GPT-5
            response = await self._call_gpt_with_tools(messages, agent_config['tools'])
            
            # 8. Сохраняем историю чата
            await self._save_chat_message(agent_id, user_id, user_message, "user", session_id)
            await self._save_chat_message(agent_id, user_id, response, "assistant", session_id)
            
            # 9. Обновляем оперативную память
            await self._update_operational_memory(agent_id, user_id, session_id, user_message, response)
            
            logger.info(f"✅ Ответ агента {agent_id} сгенерирован успешно")
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа агента {agent_id}: {e}")
            return f"❌ Техническая ошибка агента {agent_id}: {str(e)}"
    
    async def _get_agent_configuration(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Получение конфигурации агента из SQL"""
        cursor = self.db_connection.cursor(dictionary=True)
        
        try:
            query = """
            SELECT agent_id, agent_name, role, persona, system_prompt, 
                   tools, rules, tone_of_voice, routing_rules, version
            FROM agent_configurations 
            WHERE agent_id = %s AND is_active = TRUE
            """
            
            cursor.execute(query, (agent_id,))
            result = cursor.fetchone()
            
            if result:
                # Парсим JSON поля
                result['tools'] = json.loads(result['tools']) if result['tools'] else []
                result['rules'] = json.loads(result['rules']) if result['rules'] else {}
                result['routing_rules'] = json.loads(result['routing_rules']) if result['routing_rules'] else {}
                
                logger.info(f"✅ Конфигурация агента {agent_id} загружена")
                return result
            else:
                logger.warning(f"⚠️ Агент {agent_id} не найден или неактивен")
                return None
                
        except Error as e:
            logger.error(f"❌ Ошибка получения конфигурации агента {agent_id}: {e}")
            return None
        finally:
            cursor.close()
    
    async def _get_operational_memory(self, agent_id: str, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """Получение оперативной памяти (контекст задач)"""
        cursor = self.db_connection.cursor(dictionary=True)
        
        try:
            query = """
            SELECT task_context, message_history, current_focus
            FROM operational_memory 
            WHERE agent_id = %s AND user_id = %s
            """
            params = [agent_id, user_id]
            
            if session_id:
                query += " AND session_id = %s"
                params.append(session_id)
            
            query += " ORDER BY updated_at DESC LIMIT 1"
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            if result:
                result['message_history'] = json.loads(result['message_history']) if result['message_history'] else []
                return result
            else:
                return {
                    'task_context': '',
                    'message_history': [],
                    'current_focus': ''
                }
                
        except Error as e:
            logger.error(f"❌ Ошибка получения оперативной памяти: {e}")
            return {'task_context': '', 'message_history': [], 'current_focus': ''}
        finally:
            cursor.close()
    
    async def _get_core_memory(self, agent_id: str) -> List[Dict[str, Any]]:
        """Получение core-памяти (правила)"""
        cursor = self.db_connection.cursor(dictionary=True)
        
        try:
            query = """
            SELECT rule_type, rule_content, priority
            FROM core_memory 
            WHERE agent_id = %s AND is_active = TRUE
            ORDER BY priority ASC, created_at ASC
            """
            
            cursor.execute(query, (agent_id,))
            results = cursor.fetchall()
            
            logger.info(f"✅ Загружено {len(results)} правил из core-памяти для {agent_id}")
            return results
            
        except Error as e:
            logger.error(f"❌ Ошибка получения core-памяти: {e}")
            return []
        finally:
            cursor.close()
    
    async def _get_chat_history(self, agent_id: str, user_id: str, session_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение истории чата"""
        cursor = self.db_connection.cursor(dictionary=True)
        
        try:
            query = """
            SELECT role, content, timestamp, metadata
            FROM chat_history 
            WHERE agent_id = %s AND user_id = %s
            """
            params = [agent_id, user_id]
            
            if session_id:
                query += " AND session_id = %s"
                params.append(session_id)
            
            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Реверсируем порядок для правильной последовательности
            results.reverse()
            
            logger.info(f"✅ Загружено {len(results)} сообщений из истории чата")
            return results
            
        except Error as e:
            logger.error(f"❌ Ошибка получения истории чата: {e}")
            return []
        finally:
            cursor.close()
    
    def _build_system_prompt(self, agent_config: Dict[str, Any], 
                           operational_memory: Dict[str, Any], 
                           core_memory: List[Dict[str, Any]]) -> str:
        """Построение системного промпта с персонализацией"""
        
        # Базовый промпт агента
        system_prompt = agent_config['system_prompt']
        
        # Добавляем core-память (правила)
        if core_memory:
            rules_section = "\n\nВАЖНЫЕ ПРАВИЛА И ПРИНЦИПЫ:\n"
            for rule in core_memory:
                rules_section += f"• {rule['rule_content']}\n"
            system_prompt += rules_section
        
        # Добавляем tone of voice
        if agent_config.get('tone_of_voice'):
            system_prompt += f"\n\nСТИЛЬ ОБЩЕНИЯ:\n{agent_config['tone_of_voice']}\n"
        
        # Добавляем оперативную память (контекст)
        if operational_memory.get('task_context'):
            system_prompt += f"\n\nТЕКУЩИЙ КОНТЕКСТ ЗАДАЧ:\n{operational_memory['task_context']}\n"
        
        if operational_memory.get('current_focus'):
            system_prompt += f"\n\nТЕКУЩИЙ ФОКУС:\n{operational_memory['current_focus']}\n"
        
        return system_prompt
    
    def _build_messages(self, system_prompt: str, chat_history: List[Dict[str, Any]], 
                       user_message: str) -> List[Dict[str, str]]:
        """Построение списка сообщений для GPT"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем историю чата
        for msg in chat_history:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    async def _call_gpt_with_tools(self, messages: List[Dict[str, str]], 
                                 tools: List[Dict[str, Any]]) -> str:
        """Вызов GPT-5 с инструментами"""
        try:
            logger.info(f"🧠 Вызов GPT-5 с {len(tools)} инструментами")
            
            # Запрос к GPT-5 Responses API
            response = await self.openai_client.responses.create(
                model=self.openai_config['model'],
                input=messages,
                tools=tools,
                tool_choice="none",  # Сначала просто общаемся, без функций
                text={"verbosity": "medium"},
                reasoning={"effort": "high"}
            )
            
            # Парсинг ответа GPT-5
            content = ""
            tool_calls = None
            
            if hasattr(response, 'output') and response.output:
                for item in response.output:
                    if hasattr(item, 'type') and item.type == 'message':
                        if hasattr(item, 'content') and item.content:
                            for content_item in item.content:
                                if hasattr(content_item, 'text') and content_item.text:
                                    content = content_item.text.strip()
                                    break
                        if hasattr(item, 'tool_calls'):
                            tool_calls = item.tool_calls
                        break
            
            if not content:
                return "❌ Ошибка: GPT-5 не смог обработать запрос"
            
            # Если GPT решил вызвать инструменты
            if tool_calls:
                logger.info(f"🔧 GPT хочет вызвать {len(tool_calls)} инструментов")
                tool_results = await self._execute_tool_calls(tool_calls)
                
                # Формируем финальный ответ с результатами инструментов
                final_response = f"{content}\n\n" + "\n\n".join(tool_results) if content else "\n\n".join(tool_results)
                return final_response
            else:
                return content
                
        except Exception as e:
            logger.error(f"❌ Ошибка вызова GPT-5: {e}")
            return f"❌ Техническая ошибка: {str(e)}"
    
    async def _execute_tool_calls(self, tool_calls: List[Any]) -> List[str]:
        """Выполнение вызовов инструментов"""
        tool_results = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            logger.info(f"🔧 Выполнение инструмента: {function_name}")
            
            try:
                # Здесь можно добавить логику выполнения различных инструментов
                # Пока возвращаем заглушку
                result = f"Инструмент {function_name} выполнен с параметрами: {arguments}"
                tool_results.append(result)
                
            except Exception as e:
                error_result = f"❌ Ошибка выполнения {function_name}: {str(e)}"
                tool_results.append(error_result)
        
        return tool_results
    
    async def _save_chat_message(self, agent_id: str, user_id: str, content: str, 
                               role: str, session_id: str = None):
        """Сохранение сообщения в историю чата"""
        cursor = self.db_connection.cursor()
        
        try:
            query = """
            INSERT INTO chat_history (agent_id, user_id, role, content, session_id, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                agent_id,
                user_id,
                role,
                content,
                session_id,
                json.dumps({"timestamp": datetime.now().isoformat()})
            ))
            
            self.db_connection.commit()
            
        except Error as e:
            logger.error(f"❌ Ошибка сохранения сообщения: {e}")
            self.db_connection.rollback()
        finally:
            cursor.close()
    
    async def _update_operational_memory(self, agent_id: str, user_id: str, session_id: str,
                                       user_message: str, agent_response: str):
        """Обновление оперативной памяти"""
        cursor = self.db_connection.cursor()
        
        try:
            # Получаем текущую оперативную память
            select_query = """
            SELECT id, message_history FROM operational_memory 
            WHERE agent_id = %s AND user_id = %s AND session_id = %s
            ORDER BY updated_at DESC LIMIT 1
            """
            
            cursor.execute(select_query, (agent_id, user_id, session_id))
            result = cursor.fetchone()
            
            if result:
                # Обновляем существующую запись
                memory_id, message_history = result
                
                # Парсим историю сообщений
                history = json.loads(message_history) if message_history else []
                
                # Добавляем новые сообщения
                history.append({"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})
                history.append({"role": "assistant", "content": agent_response, "timestamp": datetime.now().isoformat()})
                
                # Ограничиваем размер истории (последние 20 сообщений)
                if len(history) > 20:
                    history = history[-20:]
                
                update_query = """
                UPDATE operational_memory 
                SET message_history = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
                
                cursor.execute(update_query, (json.dumps(history), memory_id))
                
            else:
                # Создаем новую запись
                insert_query = """
                INSERT INTO operational_memory (agent_id, user_id, session_id, message_history, current_focus)
                VALUES (%s, %s, %s, %s, %s)
                """
                
                new_history = [
                    {"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()},
                    {"role": "assistant", "content": agent_response, "timestamp": datetime.now().isoformat()}
                ]
                
                cursor.execute(insert_query, (
                    agent_id,
                    user_id,
                    session_id,
                    json.dumps(new_history),
                    "Активная беседа"
                ))
            
            self.db_connection.commit()
            
        except Error as e:
            logger.error(f"❌ Ошибка обновления оперативной памяти: {e}")
            self.db_connection.rollback()
        finally:
            cursor.close()
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Получение статуса агента"""
        try:
            agent_config = await self._get_agent_configuration(agent_id)
            
            if agent_config:
                return {
                    "agent_id": agent_id,
                    "agent_name": agent_config['agent_name'],
                    "role": agent_config['role'],
                    "status": "active",
                    "model": self.openai_config['model'],
                    "version": agent_config['version'],
                    "timestamp": datetime.now().isoformat(),
                    "description": f"Агент {agent_config['role']} готов к работе"
                }
            else:
                return {
                    "agent_id": agent_id,
                    "status": "not_found",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса агента {agent_id}: {e}")
            return {
                "agent_id": agent_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("🛑 Завершение работы Unified LLM Service...")
        
        try:
            if self.db_connection and self.db_connection.is_connected():
                self.db_connection.close()
                logger.info("🔒 Соединение с базой данных закрыто")
            
            if hasattr(self.openai_client, '_client'):
                await self.openai_client._client.aclose()
                logger.info("🔒 OpenAI клиент закрыт")
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при закрытии ресурсов: {e}")
        
        logger.info("✅ Unified LLM Service завершил работу")
