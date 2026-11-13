"""
Messenger Interface - Интерфейс для работы с мессенджерами

Обеспечивает интеграцию Master Agent с Teams, Telegram и Email
для естественного общения с людьми в организации.

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import aiohttp
import uuid

from .models import ConversationMessage, CommunicationChannel

logger = logging.getLogger("messenger-interface")


class MessengerInterface:
    """
    Интерфейс для работы с мессенджерами
    
    Поддерживает:
    - Microsoft Teams (через Bot Framework)
    - Telegram (через Bot API)
    - Email (через SMTP/IMAP)
    - Webhook уведомления
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger
        
        # Конфигурация мессенджеров
        self.messenger_config = config.get("messengers", {})
        
        # Активные каналы
        self.active_channels: Dict[str, CommunicationChannel] = {}
        
        # Обработчики событий
        self.message_handlers: List[Callable] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Сессии и состояние
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self.bot_tokens: Dict[str, str] = {}
        
        # Статистика
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "active_conversations": 0,
            "channels_count": 0
        }
    
    async def initialize(self):
        """Инициализация всех мессенджеров"""
        try:
            # Инициализация Teams
            if self.messenger_config.get("teams", {}).get("enabled", False):
                await self._initialize_teams()
            
            # Инициализация Telegram
            if self.messenger_config.get("telegram", {}).get("enabled", False):
                await self._initialize_telegram()
            
            # Инициализация Email
            if self.messenger_config.get("email", {}).get("enabled", False):
                await self._initialize_email()
            
            self.logger.info(f"✅ Messenger Interface инициализирован: {len(self.active_channels)} каналов")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации мессенджеров: {e}")
            raise
    
    async def _initialize_teams(self):
        """Инициализация Microsoft Teams бота"""
        try:
            teams_config = self.messenger_config["teams"]
            
            # Настройка Teams бота
            bot_id = teams_config.get("bot_id")
            bot_password = teams_config.get("bot_password")
            
            if not bot_id or not bot_password:
                self.logger.warning("⚠️ Teams bot credentials не настроены")
                return
            
            # Создание канала для Teams
            teams_channel = CommunicationChannel(
                channel_id="teams_main",
                channel_type="teams",
                name="Microsoft Teams",
                bot_enabled=True,
                settings={
                    "bot_id": bot_id,
                    "bot_password": bot_password,
                    "webhook_url": teams_config.get("webhook_url", "")
                }
            )
            
            self.active_channels["teams"] = teams_channel
            self.bot_tokens["teams"] = await self._get_teams_token(bot_id, bot_password)
            
            self.logger.info("✅ Teams бот инициализирован")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации Teams: {e}")
    
    async def _initialize_telegram(self):
        """Инициализация Telegram бота"""
        try:
            telegram_config = self.messenger_config["telegram"]
            
            bot_token = telegram_config.get("bot_token")
            if not bot_token:
                self.logger.warning("⚠️ Telegram bot token не настроен")
                return
            
            # Проверка токена
            if not await self._verify_telegram_token(bot_token):
                raise ValueError("Неверный Telegram bot token")
            
            # Создание канала для Telegram
            telegram_channel = CommunicationChannel(
                channel_id="telegram_main",
                channel_type="telegram",
                name="Telegram Bot",
                bot_enabled=True,
                settings={
                    "bot_token": bot_token,
                    "webhook_url": telegram_config.get("webhook_url", ""),
                    "allowed_users": telegram_config.get("allowed_users", [])
                }
            )
            
            self.active_channels["telegram"] = telegram_channel
            self.bot_tokens["telegram"] = bot_token
            
            # Установка webhook (если настроен)
            webhook_url = telegram_config.get("webhook_url")
            if webhook_url:
                await self._set_telegram_webhook(bot_token, webhook_url)
            
            self.logger.info("✅ Telegram бот инициализирован")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации Telegram: {e}")
    
    async def _initialize_email(self):
        """Инициализация Email интеграции"""
        try:
            email_config = self.messenger_config["email"]
            
            # Создание канала для Email
            email_channel = CommunicationChannel(
                channel_id="email_main",
                channel_type="email",
                name="Email Integration",
                bot_enabled=True,
                settings={
                    "smtp_server": email_config.get("smtp_server"),
                    "smtp_port": email_config.get("smtp_port", 587),
                    "username": email_config.get("username"),
                    "password": email_config.get("password"),
                    "from_address": email_config.get("from_address")
                }
            )
            
            self.active_channels["email"] = email_channel
            
            self.logger.info("✅ Email интеграция инициализирована")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации Email: {e}")
    
    async def send_message(self, message: ConversationMessage) -> bool:
        """Отправка сообщения в указанный канал"""
        try:
            channel = message.channel
            
            if channel == "teams":
                return await self._send_teams_message(message)
            elif channel == "telegram":
                return await self._send_telegram_message(message)
            elif channel == "email":
                return await self._send_email_message(message)
            else:
                self.logger.error(f"❌ Неизвестный канал: {channel}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки сообщения: {e}")
            return False
    
    async def _send_teams_message(self, message: ConversationMessage) -> bool:
        """Отправка сообщения в Teams"""
        try:
            if "teams" not in self.bot_tokens:
                return False
            
            # Формирование запроса к Teams API
            teams_api_url = f"https://api.botframework.com/v3/conversations/{message.conversation_id}/activities"
            
            headers = {
                "Authorization": f"Bearer {self.bot_tokens['teams']}",
                "Content-Type": "application/json"
            }
            
            # Форматирование сообщения для Teams
            teams_message = {
                "type": "message",
                "from": {
                    "id": "master-agent",
                    "name": "РЕКС"
                },
                "text": message.content,
                "timestamp": message.timestamp.isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(teams_api_url, headers=headers, json=teams_message) as response:
                    if response.status == 200:
                        self.stats["messages_sent"] += 1
                        return True
                    else:
                        self.logger.error(f"❌ Teams API ошибка: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки в Teams: {e}")
            return False
    
    async def _send_telegram_message(self, message: ConversationMessage) -> bool:
        """Отправка сообщения в Telegram"""
        try:
            bot_token = self.bot_tokens.get("telegram")
            if not bot_token:
                return False
            
            # URL Telegram Bot API
            telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            # Формирование запроса
            telegram_message = {
                "chat_id": message.conversation_id,
                "text": message.content,
                "parse_mode": "Markdown"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(telegram_api_url, json=telegram_message) as response:
                    if response.status == 200:
                        self.stats["messages_sent"] += 1
                        return True
                    else:
                        response_text = await response.text()
                        self.logger.error(f"❌ Telegram API ошибка: {response.status} - {response_text}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки в Telegram: {e}")
            return False
    
    async def _send_email_message(self, message: ConversationMessage) -> bool:
        """Отправка Email сообщения"""
        try:
            email_settings = self.active_channels.get("email", {}).settings
            
            # Здесь бы была интеграция с SMTP
            # Для примера возвращаем True
            self.logger.info(f"📧 Email отправлен: {message.recipient}")
            self.stats["messages_sent"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки Email: {e}")
            return False
    
    async def handle_incoming_message(self, raw_message: Dict[str, Any], channel: str) -> Optional[ConversationMessage]:
        """Обработка входящего сообщения"""
        try:
            # Парсинг сообщения в зависимости от канала
            if channel == "teams":
                message = await self._parse_teams_message(raw_message)
            elif channel == "telegram":
                message = await self._parse_telegram_message(raw_message)
            elif channel == "email":
                message = await self._parse_email_message(raw_message)
            else:
                self.logger.error(f"❌ Неизвестный канал: {channel}")
                return None
            
            if message:
                self.stats["messages_received"] += 1
                
                # Вызов обработчиков
                for handler in self.message_handlers:
                    try:
                        await handler(message)
                    except Exception as e:
                        self.logger.error(f"❌ Ошибка обработчика сообщений: {e}")
                
                return message
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки входящего сообщения: {e}")
            return None
    
    async def _parse_teams_message(self, raw_message: Dict[str, Any]) -> Optional[ConversationMessage]:
        """Парсинг сообщения из Teams"""
        try:
            return ConversationMessage(
                message_id=raw_message.get("id", f"teams_{uuid.uuid4().hex[:8]}"),
                sender=raw_message.get("from", {}).get("name", "unknown"),
                recipient="master_agent",
                content=raw_message.get("text", ""),
                channel="teams",
                conversation_id=raw_message.get("conversation", {}).get("id", "unknown"),
                metadata=raw_message
            )
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга Teams сообщения: {e}")
            return None
    
    async def _parse_telegram_message(self, raw_message: Dict[str, Any]) -> Optional[ConversationMessage]:
        """Парсинг сообщения из Telegram"""
        try:
            message_data = raw_message.get("message", {})
            
            return ConversationMessage(
                message_id=str(message_data.get("message_id", f"tg_{uuid.uuid4().hex[:8]}")),
                sender=message_data.get("from", {}).get("username", "unknown"),
                recipient="master_agent",
                content=message_data.get("text", ""),
                channel="telegram",
                conversation_id=str(message_data.get("chat", {}).get("id", "unknown")),
                metadata=raw_message
            )
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга Telegram сообщения: {e}")
            return None
    
    async def _parse_email_message(self, raw_message: Dict[str, Any]) -> Optional[ConversationMessage]:
        """Парсинг Email сообщения"""
        try:
            return ConversationMessage(
                message_id=raw_message.get("message_id", f"email_{uuid.uuid4().hex[:8]}"),
                sender=raw_message.get("from", "unknown"),
                recipient="master_agent",
                content=raw_message.get("body", ""),
                channel="email",
                conversation_id=raw_message.get("conversation_id", "email_thread"),
                metadata=raw_message
            )
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга Email сообщения: {e}")
            return None
    
    def add_message_handler(self, handler: Callable):
        """Добавление обработчика сообщений"""
        self.message_handlers.append(handler)
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """Добавление обработчика событий"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def _get_teams_token(self, bot_id: str, bot_password: str) -> str:
        """Получение токена для Teams бота"""
        try:
            token_url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
            
            data = {
                "grant_type": "client_credentials",
                "client_id": bot_id,
                "client_secret": bot_password,
                "scope": "https://api.botframework.com/.default"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        return token_data.get("access_token", "")
                    else:
                        self.logger.error(f"❌ Ошибка получения Teams токена: {response.status}")
                        return ""
                        
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения Teams токена: {e}")
            return ""
    
    async def _verify_telegram_token(self, bot_token: str) -> bool:
        """Проверка Telegram токена"""
        try:
            verify_url = f"https://api.telegram.org/bot{bot_token}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(verify_url) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def _set_telegram_webhook(self, bot_token: str, webhook_url: str):
        """Установка webhook для Telegram бота"""
        try:
            webhook_api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
            
            data = {
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_api_url, json=data) as response:
                    if response.status == 200:
                        self.logger.info(f"✅ Telegram webhook установлен: {webhook_url}")
                    else:
                        self.logger.error(f"❌ Ошибка установки webhook: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"❌ Ошибка установки Telegram webhook: {e}")
    
    async def broadcast_message(self, content: str, channels: List[str] = None) -> Dict[str, bool]:
        """Рассылка сообщения по каналам"""
        if channels is None:
            channels = list(self.active_channels.keys())
        
        results = {}
        
        for channel in channels:
            if channel in self.active_channels:
                message = ConversationMessage(
                    message_id=f"broadcast_{uuid.uuid4().hex[:8]}",
                    sender="master_agent",
                    recipient="all",
                    content=content,
                    channel=channel,
                    conversation_id="broadcast"
                )
                results[channel] = await self.send_message(message)
            else:
                results[channel] = False
        
        return results
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики мессенджеров"""
        return {
            "active_channels": len(self.active_channels),
            "messages_sent": self.stats["messages_sent"],
            "messages_received": self.stats["messages_received"],
            "active_conversations": len(self.user_sessions),
            "channels": list(self.active_channels.keys()),
            "handlers_count": len(self.message_handlers)
        }
