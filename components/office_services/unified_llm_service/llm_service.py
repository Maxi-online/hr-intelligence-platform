"""
Single LLM Microservice GPT-5
Receives information from SQL to respond to an agent and simulates an agent's response
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
    'A single LLM microservice for all agents'
    
    def __init__(self, openai_config: Dict[str, Any], db_config: Dict[str, Any]):
        self.openai_config = openai_config
        self.db_config = db_config
        self.db_connection = None
        
        # OpenAI client initialization with proxy
        self._init_openai_client()
        
        logger.info('🤖 Universal LLM Service initialized')
    
    def _init_openai_client(self):
        'OpenAI client initialization with proxy'
        proxy_url = self.openai_config.get('proxy_url')
        
        if proxy_url:
            logger.info(f"🔧 OpenAI with Proxi: {proxy_url}")
            
            http_client = httpx.AsyncClient(
                proxy=proxy_url,
                timeout=30.0
            )
            
            self.openai_client = AsyncOpenAI(
                api_key=self.openai_config['api_key'],
                http_client=http_client
            )
            logger.info('✅ OpenAI client set up with proxi')
        else:
            raise ValueError('Proxie has a duty! Add proxy_url in configuration')
    
    async def initialize(self):
        'Initialization of service'
        await self._connect_to_database()
        logger.info('✅ Universal LLM Service is ready for work')
    
    async def _connect_to_database(self):
        'Connecting to a centralized PostgreSQL database'
        try:
            self.db_connection = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database']
            )
            logger.info('✅ The connection to the central PostgreSQL database has been installed')
        except Exception as e:
            logger.error(f"❌ Error of connection to the database: {e}")
            raise
    
    async def generate_agent_response(self, agent_id: str, user_message: str, 
                                    user_id: str, session_id: str = None) -> str:
        """
        Agent response generation based on SQL configuration
        
        Args:
            agent_id: ID agent (boss_ai, alena_ai, sergei_ai)
            user_message: Incoming User Message
            user_id: User ID
            session_id: ID session (optimal)
            
        Returns:
            str: Agent &apos; s response
        """
        logger.info(f"🎯 Agent response generation {agent_id} for user {user_id}")
        
        try:
            # 1. Get the SQL Agent configuration
            agent_config = await self._get_agent_configuration(agent_id)
            if not agent_config:
                return f"❌ Agent {agent_id} not found in the database"
            
            # 2. Improve memory (context of task))
            operational_memory = await self._get_operational_memory(agent_id, user_id, session_id)
            
            # 3. Core Memory (Rules of Memory))
            core_memory = await self._get_core_memory(agent_id)
            
            # 4. Getting the chat history.
            chat_history = await self._get_chat_history(agent_id, user_id, session_id)
            
            # 5. Forming a system prompto with personalization
            system_prompt = self._build_system_prompt(agent_config, operational_memory, core_memory)
            
            # 6. Form messages for GPT
            messages = self._build_messages(system_prompt, chat_history, user_message)
            
            # 7. Generate the answer through GPT-5
            response = await self._call_gpt_with_tools(messages, agent_config['tools'])
            
            # 8. Save Chat's History
            await self._save_chat_message(agent_id, user_id, user_message, "user", session_id)
            await self._save_chat_message(agent_id, user_id, response, "assistant", session_id)
            
            # 9. Updates of operational memory
            await self._update_operational_memory(agent_id, user_id, session_id, user_message, response)
            
            logger.info(f"✅ Agent's Response {agent_id} Generated successfully")
            return response
            
        except Exception as e:
            logger.error(f"❌ Errors of the Agent's Answer Generation {agent_id}: {e}")
            return f"❌ Technical error of the agent {agent_id}: {str(e)}"
    
    async def _get_agent_configuration(self, agent_id: str) -> Optional[Dict[str, Any]]:
        'Receive SQL Agent configuration'
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
                # JSON field parsim
                result['tools'] = json.loads(result['tools']) if result['tools'] else []
                result['rules'] = json.loads(result['rules']) if result['rules'] else {}
                result['routing_rules'] = json.loads(result['routing_rules']) if result['routing_rules'] else {}
                
                logger.info(f"✅ Agent configuration {agent_id} loaded")
                return result
            else:
                logger.warning(f"⚠️ Agent {agent_id} not found or inactive")
                return None
                
        except Error as e:
            logger.error(f"❌ Configuration error of the agent {agent_id}: {e}")
            return None
        finally:
            cursor.close()
    
    async def _get_operational_memory(self, agent_id: str, user_id: str, session_id: str = None) -> Dict[str, Any]:
        'Acquisition of operational memory (context of tasks))'
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
            logger.error(f"❌ Error in obtaining operational memory: {e}")
            return {'task_context': '', 'message_history': [], 'current_focus': ''}
        finally:
            cursor.close()
    
    async def _get_core_memory(self, agent_id: str) -> List[Dict[str, Any]]:
        'Recovery of Core Memory (Rules))'
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
            
            logger.info(f"✅ Loaded {len(results)} The core memory for {agent_id}")
            return results
            
        except Error as e:
            logger.error(f"❌ Error of Core Memory: {e}")
            return []
        finally:
            cursor.close()
    
    async def _get_chat_history(self, agent_id: str, user_id: str, session_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        'Getting the chat history'
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
            
            # Reverse order for the correct sequence
            results.reverse()
            
            logger.info(f"✅ Loaded {len(results)} chat history")
            return results
            
        except Error as e:
            logger.error(f"❌ Error in getting a chat history: {e}")
            return []
        finally:
            cursor.close()
    
    def _build_system_prompt(self, agent_config: Dict[str, Any], 
                           operational_memory: Dict[str, Any], 
                           core_memory: List[Dict[str, Any]]) -> str:
        'Building a system prompt with personalization'
        
        # Basic agent prompt
        system_prompt = agent_config['system_prompt']
        
        # Add Core Memory (Rules))
        if core_memory:
            rules_section = '\n\nMAIN RULES AND PRINCIPLES:\n'
            for rule in core_memory:
                rules_section += f"• {rule['rule_content']}\n"
            system_prompt += rules_section
        
        # Add tone of voice
        if agent_config.get('tone_of_voice'):
            system_prompt += f"\n\nSTYL COMMUNICATION:\n{agent_config['tone_of_voice']}\n"
        
        # Add operational memory (context))
        if operational_memory.get('task_context'):
            system_prompt += f"\n\nENT:\n{operational_memory['task_context']}\n"
        
        if operational_memory.get('current_focus'):
            system_prompt += f"\n\nENT FOCUS:\n{operational_memory['current_focus']}\n"
        
        return system_prompt
    
    def _build_messages(self, system_prompt: str, chat_history: List[Dict[str, Any]], 
                       user_message: str) -> List[Dict[str, str]]:
        'Building a message list for GPT'
        messages = [{"role": "system", "content": system_prompt}]
        
        # Adding chat history
        for msg in chat_history:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    async def _call_gpt_with_tools(self, messages: List[Dict[str, str]], 
                                 tools: List[Dict[str, Any]]) -> str:
        'GPT-5 call with tools'
        try:
            logger.info(f"🧠 GPT-5 call c {len(tools)} instruments")
            
            # Request for GPT-5 Responses API
            response = await self.openai_client.responses.create(
                model=self.openai_config['model'],
                input=messages,
                tools=tools,
                tool_choice="none",  # First we just talk, no functions.
                text={"verbosity": "medium"},
                reasoning={"effort": "high"}
            )
            
            # Parsing Response GPT-5
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
                return '❌ Error: GPT-5 failed to process the request'
            
            # If GPT decided to call the tools
            if tool_calls:
                logger.info(f"🔧 GPT wants to call {len(tool_calls)} Tools")
                tool_results = await self._execute_tool_calls(tool_calls)
                
                # Form the final response with the results of the tools
                final_response = f"{content}\n\n" + "\n\n".join(tool_results) if content else "\n\n".join(tool_results)
                return final_response
            else:
                return content
                
        except Exception as e:
            logger.error(f"❌ The error of calling GPT-5: {e}")
            return f"❌ Technical errors: {str(e)}"
    
    async def _execute_tool_calls(self, tool_calls: List[Any]) -> List[str]:
        'Meeting the challenges of the instruments'
        tool_results = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            logger.info(f"🔧 Implementation of the instrument: {function_name}")
            
            try:
                # Here we can add the logic of implementing the various instruments
                # While we return the plug.
                result = f"Instrument {function_name} with parameters: {arguments}"
                tool_results.append(result)
                
            except Exception as e:
                error_result = f"❌ Error of execution {function_name}: {str(e)}"
                tool_results.append(error_result)
        
        return tool_results
    
    async def _save_chat_message(self, agent_id: str, user_id: str, content: str, 
                               role: str, session_id: str = None):
        'Keeping the message in chat history'
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
            logger.error(f"❌ Error in keeping the message: {e}")
            self.db_connection.rollback()
        finally:
            cursor.close()
    
    async def _update_operational_memory(self, agent_id: str, user_id: str, session_id: str,
                                       user_message: str, agent_response: str):
        'Updated operational memory'
        cursor = self.db_connection.cursor()
        
        try:
            # Get current operational memory
            select_query = """
            SELECT id, message_history FROM operational_memory 
            WHERE agent_id = %s AND user_id = %s AND session_id = %s
            ORDER BY updated_at DESC LIMIT 1
            """
            
            cursor.execute(select_query, (agent_id, user_id, session_id))
            result = cursor.fetchone()
            
            if result:
                # Update existing entry
                memory_id, message_history = result
                
                # Parse the message history.
                history = json.loads(message_history) if message_history else []
                
                # Adding new messages
                history.append({"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})
                history.append({"role": "assistant", "content": agent_response, "timestamp": datetime.now().isoformat()})
                
                # Limiting the size of history (20 last messages)
                if len(history) > 20:
                    history = history[-20:]
                
                update_query = """
                UPDATE operational_memory 
                SET message_history = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
                
                cursor.execute(update_query, (json.dumps(history), memory_id))
                
            else:
                # Create a new recording
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
                    'Active conversation'
                ))
            
            self.db_connection.commit()
            
        except Error as e:
            logger.error(f"❌ Errors in operational memory update: {e}")
            self.db_connection.rollback()
        finally:
            cursor.close()
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        'Getting Agent Status'
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
                    "description": f"Agent {agent_config['role']} Ready to work."
                }
            else:
                return {
                    "agent_id": agent_id,
                    "status": "not_found",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Error in obtaining the status of agent {agent_id}: {e}")
            return {
                "agent_id": agent_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup(self):
        'Cleaning of resources'
        logger.info('🛑 Completion of Universal LLM Service...')
        
        try:
            if self.db_connection and self.db_connection.is_connected():
                self.db_connection.close()
                logger.info('🔒 The connection to the database is closed')
            
            if hasattr(self.openai_client, '_client'):
                await self.openai_client._client.aclose()
                logger.info('🔒 OpenAI client closed')
                
        except Exception as e:
            logger.warning(f"⚠️ Error in closing resources: {e}")
        
        logger.info('✅ Universal LLM Service has completed its work')
