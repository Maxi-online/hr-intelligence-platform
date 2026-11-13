"""
Centralized Supervisor микросервис GPT-5
Управляет командой агентов через централизованную базу данных
"""

import asyncio
import json
import logging
import psycopg2
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import httpx

logger = logging.getLogger(__name__)

class CentralizedSupervisor:
    """Централизованный Supervisor для управления агентами"""
    
    def __init__(self, openai_config: Dict[str, Any], db_config: Dict[str, Any]):
        self.openai_config = openai_config
        self.db_config = db_config
        self.openai_client = None
        self.db_connection = None
        
        # Инициализация OpenAI клиента
        self._init_openai_client()
    
    def _init_openai_client(self):
        """Инициализация OpenAI клиента с прокси"""
        try:
            proxy_url = self.openai_config.get('proxy_url')
            if proxy_url:
                logger.info(f"🔧 Настройка прокси: {proxy_url}")
                http_client = httpx.AsyncClient(proxy=proxy_url, timeout=30.0)
                self.openai_client = AsyncOpenAI(
                    api_key=self.openai_config['api_key'],
                    http_client=http_client
                )
                logger.info(f"✅ OpenAI клиент настроен с прокси: {proxy_url}")
            else:
                logger.error("❌ ОШИБКА: proxy_url НЕ НАЙДЕН!")
                raise ValueError("Прокси ОБЯЗАТЕЛЕН! Добавьте proxy_url в конфигурацию")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации OpenAI клиента: {e}")
            raise
    
    async def initialize(self):
        """Инициализация Supervisor"""
        logger.info("🤖 Инициализация Centralized Supervisor...")
        try:
            await self._connect_to_database()
            logger.info("✅ Centralized Supervisor готов")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Supervisor: {e}")
            raise
    
    async def _connect_to_database(self):
        """Подключение к централизованной базе данных"""
        try:
            self.db_connection = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database']
            )
            logger.info("✅ Подключение к централизованной базе данных установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            raise
    
    async def process_message(self, user_message: str, user_id: str, session_id: str = None) -> str:
        """Обработка сообщения пользователя через Supervisor"""
        logger.info(f"📥 Supervisor обрабатывает: {user_message}")
        
        try:
            # Сохраняем сообщение пользователя
            await self._save_chat_message("supervisor_001", user_id, user_message, "user", session_id)
            
            # Обрабатываем через Supervisor с инструментами
            response = await self._supervisor_with_tools(user_message, user_id, session_id)
            
            # Сохраняем ответ Supervisor
            await self._save_chat_message("supervisor_001", user_id, response, "assistant", session_id)
            
            logger.info(f"✅ Supervisor ответил: {response[:100]}...")
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки в Supervisor: {e}")
            error_response = f"❌ Произошла ошибка при обработке запроса: {str(e)}"
            
            try:
                await self._save_chat_message("supervisor_001", user_id, error_response, "assistant", session_id)
            except:
                pass  # Игнорируем ошибки сохранения при основной ошибке
            
            return error_response
    
    async def _supervisor_with_tools(self, user_message: str, user_id: str, session_id: str = None) -> str:
        """Supervisor с инструментами управления агентами"""
        
        # Получаем конфигурацию Supervisor из базы данных
        supervisor_config = await self._get_agent_configuration("supervisor_001")
        if not supervisor_config:
            return "❌ Ошибка: Конфигурация Supervisor не найдена в базе данных"
        
        # Получаем оперативную память
        operational_memory = await self._get_operational_memory("supervisor_001", user_id, session_id)
        
        # Получаем core память
        core_memory = await self._get_core_memory("supervisor_001")
        
        # Получаем историю чата
        chat_history = await self._get_chat_history("supervisor_001", user_id, session_id, limit=5)
        
        # Формируем системный промпт
        system_prompt = self._build_system_prompt(supervisor_config, operational_memory, core_memory, chat_history)
        
        # Получаем инструменты
        tools = supervisor_config.get('tools', [])
        
        try:
            # Формируем сообщения для GPT-5
            messages = self._build_messages(system_prompt, chat_history, user_message)
            
            logger.info(f"🔍 Supervisor отправляет запрос к GPT-5: {self.openai_config['model']}")
            
            # Запрос к GPT-5 Responses API
            response = await self.openai_client.responses.create(
                model=self.openai_config['model'],
                input=messages,
                tools=tools,
                tool_choice="auto",  # Автоматический выбор инструментов
                text={"verbosity": "medium"},
                reasoning={"effort": "high"}
            )
            
            # Обрабатываем ответ GPT-5
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
                logger.error("❌ GPT-5 не вернул контент")
                return "❌ Ошибка: GPT-5 не смог обработать запрос. Попробуйте переформулировать."
            
            logger.info(f"📄 GPT-5 content: {content[:100]}...")
            logger.info(f"GPT-5 decision: {'FUNCTION CALLS' if tool_calls else 'DIRECT RESPONSE'}")
            
            # Если GPT решил вызвать функции
            if tool_calls:
                logger.info(f"GPT calling {len(tool_calls)} functions")
                tool_results = await self._execute_tool_calls(tool_calls)
                
                # Формируем финальный ответ с результатами tools
                final_response = f"{content}\n\n" + "\n\n".join(tool_results) if content else "\n\n".join(tool_results)
                return final_response
            else:
                # GPT решил НЕ вызывать инструменты - простое общение
                return content
                
        except Exception as e:
            logger.error(f"❌ Ошибка GPT-5 запроса в Supervisor: {e}")
            return f"❌ Техническая ошибка Supervisor: {str(e)}"
    
    async def _get_agent_configuration(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Получение конфигурации агента из базы данных"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT agent_name, role, persona, system_prompt, tools, rules, 
                       tone_of_voice, training_data, routing_rules, version
                FROM agent_configurations 
                WHERE agent_id = %s AND is_active = true
            """, (agent_id,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    'agent_name': result[0],
                    'role': result[1],
                    'persona': result[2],
                    'system_prompt': result[3],
                    'tools': json.loads(result[4]) if result[4] else [],
                    'rules': json.loads(result[5]) if result[5] else {},
                    'tone_of_voice': result[6],
                    'training_data': json.loads(result[7]) if result[7] else {},
                    'routing_rules': json.loads(result[8]) if result[8] else {},
                    'version': result[9]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения конфигурации агента {agent_id}: {e}")
            return None
    
    async def _get_operational_memory(self, agent_id: str, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """Получение оперативной памяти агента"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT task_context, message_history, current_focus
                FROM operational_memory 
                WHERE agent_id = %s AND user_id = %s AND session_id = %s
                ORDER BY updated_at DESC LIMIT 1
            """, (agent_id, user_id, session_id))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    'task_context': result[0] or "",
                    'message_history': json.loads(result[1]) if result[1] else [],
                    'current_focus': result[2] or ""
                }
            return {
                'task_context': "",
                'message_history': [],
                'current_focus': ""
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения оперативной памяти: {e}")
            return {'task_context': "", 'message_history': [], 'current_focus': ""}
    
    async def _get_core_memory(self, agent_id: str) -> List[Dict[str, Any]]:
        """Получение core памяти агента"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT rule_type, rule_content, priority
                FROM core_memory 
                WHERE agent_id = %s AND is_active = true
                ORDER BY priority DESC
            """, (agent_id,))
            
            results = cursor.fetchall()
            cursor.close()
            
            return [
                {
                    'rule_type': row[0],
                    'rule_content': row[1],
                    'priority': row[2]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения core памяти: {e}")
            return []
    
    async def _get_chat_history(self, agent_id: str, user_id: str, session_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение истории чата"""
        try:
            cursor = self.db_connection.cursor()
            query = """
                SELECT role, content, timestamp
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
            cursor.close()
            
            return [
                {
                    'role': row[0],
                    'content': row[1],
                    'timestamp': row[2]
                }
                for row in reversed(results)  # Возвращаем в хронологическом порядке
            ]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории чата: {e}")
            return []
    
    def _build_system_prompt(self, agent_config: Dict[str, Any], 
                           operational_memory: Dict[str, Any], 
                           core_memory: List[Dict[str, Any]],
                           chat_history: List[Dict[str, Any]]) -> str:
        """Построение системного промпта"""
        
        # Базовый системный промпт
        base_prompt = agent_config.get('system_prompt', '')
        
        # Добавляем оперативную память
        if operational_memory.get('current_focus'):
            base_prompt += f"\n\nТЕКУЩИЙ ФОКУС: {operational_memory['current_focus']}"
        
        # Добавляем core память
        if core_memory:
            core_rules = "\n".join([f"- {rule['rule_content']}" for rule in core_memory[:3]])
            base_prompt += f"\n\nCORE ПАМЯТЬ:\n{core_rules}"
        
        return base_prompt
    
    def _build_messages(self, system_prompt: str, chat_history: List[Dict[str, Any]], 
                       user_message: str) -> List[Dict[str, str]]:
        """Построение сообщений для GPT"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем историю чата
        for msg in chat_history:
            messages.append({"role": msg['role'], "content": msg['content']})
        
        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    async def _execute_tool_calls(self, tool_calls: List[Any]) -> List[str]:
        """Выполнение вызовов инструментов"""
        tool_results = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            logger.info(f"Calling {function_name} with parameters: {arguments}")
            
            if function_name == "get_system_info":
                result = await self._get_system_info(**arguments)
                tool_results.append(f"📊 Информация о системе: {result}")
            elif function_name == "get_agent_status":
                result = await self._get_agent_status(**arguments)
                tool_results.append(f"🔍 Статус агента: {result}")
            elif function_name == "get_statistics":
                result = await self._get_statistics(**arguments)
                tool_results.append(f"📈 Статистика: {result}")
            else:
                tool_results.append(f"❓ Неизвестный инструмент: {function_name}")
        
        return tool_results
    
    # === ИНСТРУМЕНТЫ SUPERVISOR ===
    
    async def _get_system_info(self, detailed: bool = False, include_metrics: bool = True):
        """Получение информации о состоянии системы"""
        try:
            cursor = self.db_connection.cursor()
            
            # Информация об агентах
            cursor.execute("SELECT COUNT(*) FROM agent_configurations WHERE is_active = true")
            active_agents = cursor.fetchone()[0]
            
            # Информация о развернутых агентах
            cursor.execute("SELECT COUNT(*) FROM deployed_agents_registry WHERE status = 'active'")
            deployed_agents = cursor.fetchone()[0]
            
            # Общее количество сообщений
            cursor.execute("SELECT COUNT(*) FROM chat_history")
            total_messages = cursor.fetchone()[0]
            
            cursor.close()
            
            system_info = {
                "active_agents": active_agents,
                "deployed_agents": deployed_agents,
                "total_messages": total_messages,
                "database_status": "connected",
                "supervisor_status": "active"
            }
            
            if include_metrics:
                system_info["metrics"] = {
                    "uptime": "running",
                    "last_activity": datetime.now().isoformat()
                }
            
            return json.dumps(system_info, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о системе: {e}")
            return f"Ошибка: {str(e)}"
    
    async def _get_agent_status(self, agent_name: str = None, include_performance: bool = True):
        """Проверка статуса агентов"""
        try:
            cursor = self.db_connection.cursor()
            
            if agent_name:
                # Статус конкретного агента
                cursor.execute("""
                    SELECT d.status, d.last_activity, d.performance_metrics
                    FROM deployed_agents_registry d
                    JOIN agent_configurations a ON d.agent_id = a.agent_id
                    WHERE a.agent_name = %s
                """, (agent_name,))
                result = cursor.fetchone()
                
                if result:
                    status_info = {
                        "agent_name": agent_name,
                        "status": result[0],
                        "last_activity": result[1].isoformat() if result[1] else None,
                        "performance_metrics": json.loads(result[2]) if result[2] else {}
                    }
                else:
                    status_info = {"agent_name": agent_name, "status": "not_found"}
            else:
                # Статус всех агентов
                cursor.execute("""
                    SELECT a.agent_name, d.status, d.last_activity
                    FROM agent_configurations a
                    LEFT JOIN deployed_agents_registry d ON a.agent_id = d.agent_id
                    WHERE a.is_active = true
                """)
                results = cursor.fetchall()
                
                status_info = {
                    "all_agents": [
                        {
                            "agent_name": row[0],
                            "status": row[1] or "not_deployed",
                            "last_activity": row[2].isoformat() if row[2] else None
                        }
                        for row in results
                    ]
                }
            
            cursor.close()
            return json.dumps(status_info, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса агентов: {e}")
            return f"Ошибка: {str(e)}"
    
    async def _get_statistics(self, period: str = "today", metrics: List[str] = None):
        """Получение статистики работы"""
        try:
            cursor = self.db_connection.cursor()
            
            # Определяем период
            if period == "today":
                time_filter = "timestamp >= CURRENT_DATE"
            elif period == "week":
                time_filter = "timestamp >= CURRENT_DATE - INTERVAL '7 days'"
            elif period == "month":
                time_filter = "timestamp >= CURRENT_DATE - INTERVAL '30 days'"
            else:
                time_filter = "1=1"
            
            # Статистика сообщений
            cursor.execute(f"SELECT COUNT(*) FROM chat_history WHERE {time_filter}")
            messages_count = cursor.fetchone()[0]
            
            # Статистика по агентам
            cursor.execute(f"""
                SELECT agent_id, COUNT(*) 
                FROM chat_history 
                WHERE {time_filter}
                GROUP BY agent_id
            """)
            agent_stats = dict(cursor.fetchall())
            
            cursor.close()
            
            statistics = {
                "period": period,
                "messages_count": messages_count,
                "agent_statistics": agent_stats,
                "generated_at": datetime.now().isoformat()
            }
            
            return json.dumps(statistics, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return f"Ошибка: {str(e)}"
    
    async def _save_chat_message(self, agent_id: str, user_id: str, content: str, 
                               role: str, session_id: str = None):
        """Сохранение сообщения в историю чата"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO chat_history (agent_id, user_id, role, content, session_id, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (agent_id, user_id, role, content, session_id, datetime.now()))
            
            self.db_connection.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сообщения: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Получение статуса Supervisor"""
        return {
            "service": "Centralized Supervisor",
            "version": "1.0.0",
            "status": "active",
            "model": self.openai_config['model'],
            "database_connected": self.db_connection is not None,
            "timestamp": datetime.now().isoformat(),
            "description": "Централизованный Supervisor для управления командой AI-агентов",
            "capabilities": [
                "Управление агентами через централизованную базу",
                "Мониторинг состояния системы",
                "Получение статистики работы",
                "Координация задач между агентами"
            ]
        }
    
    async def cleanup(self):
        """Очистка ресурсов Supervisor"""
        logger.info("🛑 Завершение работы Centralized Supervisor...")
        try:
            if self.db_connection:
                self.db_connection.close()
            if hasattr(self.openai_client, '_client'):
                await self.openai_client._client.aclose()
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при закрытии ресурсов: {e}")
        logger.info("✅ Centralized Supervisor завершил работу")
