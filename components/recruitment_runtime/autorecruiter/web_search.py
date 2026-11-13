"""
AutoGPT Web Search Tool - Поиск в интернете

Обеспечивает AutoGPT агенту доступ к интернету для:
- Поиска актуальной информации
- Исследования трендов
- Получения данных о компаниях
- Анализа рынка труда

Author: Candidate Analysis Team  
Version: 1.0.0
"""

import asyncio
import aiohttp
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger("web-search")

class WebSearchTool:
    """
    Инструмент для поиска в интернете
    
    Возможности:
    - Поиск через Google Search API
    - Поиск новостей
    - Поиск информации о компаниях
    - Анализ трендов
    """
    
    def __init__(self, google_api_key: str = None, search_engine_id: str = None):
        self.google_api_key = google_api_key or "demo_key"
        self.search_engine_id = search_engine_id or "demo_engine"
        
        # Базовые URL для поиска
        self.google_search_url = "https://www.googleapis.com/customsearch/v1"
        self.duckduckgo_url = "https://api.duckduckgo.com/"
        
        # Статистика
        self.search_stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0
        }
        
        logger.info("🌐 Web Search Tool инициализирован")
    
    async def search(self, query: str, num_results: int = 10, 
                    search_type: str = "general") -> List[Dict[str, Any]]:
        """
        Основной метод поиска
        
        Args:
            query: Поисковый запрос
            num_results: Количество результатов
            search_type: Тип поиска (general, news, companies, trends)
        """
        try:
            self.search_stats["total_searches"] += 1
            
            logger.info(f"🔍 Поиск: {query} (тип: {search_type})")
            
            # Выбираем метод поиска
            if search_type == "news":
                results = await self._search_news(query, num_results)
            elif search_type == "companies":
                results = await self._search_companies(query, num_results)
            elif search_type == "trends":
                results = await self._search_trends(query, num_results)
            else:
                results = await self._general_search(query, num_results)
            
            self.search_stats["successful_searches"] += 1
            logger.info(f"✅ Найдено {len(results)} результатов")
            
            return results
            
        except Exception as e:
            self.search_stats["failed_searches"] += 1
            logger.error(f"❌ Ошибка поиска: {e}")
            return []
    
    async def _general_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Общий поиск через Google Custom Search"""
        try:
            # Пробуем Google Custom Search API
            results = await self._google_search(query, num_results)
            
            if not results:
                # Fallback к DuckDuckGo
                results = await self._duckduckgo_search(query, num_results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка общего поиска: {e}")
            return self._create_mock_results(query, num_results)
    
    async def _google_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Поиск через Google Custom Search API"""
        try:
            params = {
                "key": self.google_api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": min(num_results, 10),
                "safe": "active"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.google_search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_google_results(data)
                    else:
                        logger.warning(f"Google Search API ошибка: {response.status}")
                        return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка Google поиска: {e}")
            return []
    
    async def _duckduckgo_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Альтернативный поиск через DuckDuckGo"""
        try:
            # Упрощенный запрос к DuckDuckGo
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.duckduckgo_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_duckduckgo_results(data, num_results)
                    else:
                        return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка DuckDuckGo поиска: {e}")
            return []
    
    async def _search_news(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Поиск новостей"""
        try:
            # Добавляем модификаторы для поиска новостей
            news_query = f"{query} news recent 2024"
            
            # Используем Google News search
            params = {
                "key": self.google_api_key,
                "cx": self.search_engine_id,
                "q": news_query,
                "num": min(num_results, 10),
                "tbm": "nws",  # News search
                "safe": "active"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.google_search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_google_results(data, result_type="news")
                    else:
                        return self._create_mock_news(query, num_results)
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска новостей: {e}")
            return self._create_mock_news(query, num_results)
    
    async def _search_companies(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Поиск информации о компаниях"""
        try:
            # Специализированный запрос для компаний
            company_query = f"{query} company information about careers jobs"
            
            results = await self._google_search(company_query, num_results)
            
            if not results:
                results = self._create_mock_company_info(query, num_results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска компаний: {e}")
            return self._create_mock_company_info(query, num_results)
    
    async def _search_trends(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Поиск трендов"""
        try:
            # Запрос для поиска трендов
            trends_query = f"{query} trends 2024 statistics market analysis"
            
            results = await self._google_search(trends_query, num_results)
            
            if not results:
                results = self._create_mock_trends(query, num_results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска трендов: {e}")
            return self._create_mock_trends(query, num_results)
    
    def _parse_google_results(self, data: Dict[str, Any], result_type: str = "general") -> List[Dict[str, Any]]:
        """Парсинг результатов Google Search"""
        try:
            results = []
            items = data.get("items", [])
            
            for item in items:
                result = {
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "google",
                    "type": result_type,
                    "found_at": datetime.now().isoformat()
                }
                
                # Дополнительные поля для новостей
                if result_type == "news" and "pagemap" in item:
                    pagemap = item["pagemap"]
                    if "metatags" in pagemap and pagemap["metatags"]:
                        metatag = pagemap["metatags"][0]
                        result["published_date"] = metatag.get("article:published_time", "")
                        result["author"] = metatag.get("author", "")
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Google результатов: {e}")
            return []
    
    def _parse_duckduckgo_results(self, data: Dict[str, Any], num_results: int) -> List[Dict[str, Any]]:
        """Парсинг результатов DuckDuckGo"""
        try:
            results = []
            
            # DuckDuckGo возвращает разные типы результатов
            related_topics = data.get("RelatedTopics", [])
            
            for topic in related_topics[:num_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    result = {
                        "title": topic.get("Text", "")[:100],
                        "link": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                        "source": "duckduckgo",
                        "type": "general",
                        "found_at": datetime.now().isoformat()
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга DuckDuckGo результатов: {e}")
            return []
    
    def _create_mock_results(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Создание mock результатов при недоступности API"""
        mock_results = []
        
        for i in range(min(num_results, 5)):
            result = {
                "title": f"Результат {i+1} для запроса '{query}'",
                "link": f"https://example.com/result-{i+1}",
                "snippet": f"Это mock результат #{i+1} для демонстрации работы поиска. Запрос: {query}",
                "source": "mock",
                "type": "general",
                "found_at": datetime.now().isoformat(),
                "_note": "Mock результат - реальный API недоступен"
            }
            mock_results.append(result)
        
        return mock_results
    
    def _create_mock_news(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Создание mock новостей"""
        mock_news = []
        
        news_topics = [
            "Тренды в IT-рекрутинге 2024",
            "Новые технологии найма персонала",
            "Изменения на рынке труда",
            "AI в подборе кадров",
            "Удаленная работа и рекрутинг"
        ]
        
        for i, topic in enumerate(news_topics[:num_results]):
            news = {
                "title": f"{topic} - {query}",
                "link": f"https://news-example.com/article-{i+1}",
                "snippet": f"Последние новости о {topic.lower()}. Аналитика и тренды в области {query}.",
                "source": "mock_news",
                "type": "news",
                "published_date": datetime.now().isoformat(),
                "author": "News Reporter",
                "found_at": datetime.now().isoformat(),
                "_note": "Mock новость - реальный API недоступен"
            }
            mock_news.append(news)
        
        return mock_news
    
    def _create_mock_company_info(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Создание mock информации о компаниях"""
        mock_companies = []
        
        for i in range(min(num_results, 3)):
            company = {
                "title": f"Компания {query} - Официальный сайт",
                "link": f"https://{query.lower().replace(' ', '')}-company.com",
                "snippet": f"Официальная информация о компании {query}. Вакансии, карьера, о компании.",
                "source": "mock_company",
                "type": "company",
                "company_size": "1000+ сотрудников",
                "industry": "IT и технологии",
                "found_at": datetime.now().isoformat(),
                "_note": "Mock информация о компании"
            }
            mock_companies.append(company)
        
        return mock_companies
    
    def _create_mock_trends(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Создание mock трендов"""
        mock_trends = []
        
        trend_topics = [
            "Рост спроса на специалистов",
            "Новые технологии в области",
            "Изменения зарплат",
            "Популярные навыки",
            "Прогнозы развития"
        ]
        
        for i, trend in enumerate(trend_topics[:num_results]):
            trend_result = {
                "title": f"{trend} - {query} 2024",
                "link": f"https://trends-example.com/trend-{i+1}",
                "snippet": f"Анализ тренда: {trend.lower()} в области {query}. Статистика и прогнозы.",
                "source": "mock_trends",
                "type": "trends",
                "trend_direction": "рост" if i % 2 == 0 else "стабильность",
                "found_at": datetime.now().isoformat(),
                "_note": "Mock тренд - реальный API недоступен"
            }
            mock_trends.append(trend_result)
        
        return mock_trends
    
    async def search_specific_site(self, query: str, site: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Поиск на конкретном сайте"""
        try:
            site_query = f"site:{site} {query}"
            return await self._general_search(site_query, num_results)
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска на сайте {site}: {e}")
            return []
    
    async def search_hh_vacancies(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Поиск вакансий на HeadHunter"""
        return await self.search_specific_site(query, "hh.ru", num_results)
    
    async def search_habr_articles(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Поиск статей на Habr"""
        return await self.search_specific_site(query, "habr.com", num_results)
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Статистика поиска"""
        return {
            **self.search_stats,
            "success_rate": (
                self.search_stats["successful_searches"] / max(self.search_stats["total_searches"], 1)
            ) * 100
        }
    
    async def verify_url_accessibility(self, url: str) -> bool:
        """Проверка доступности URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=10) as response:
                    return response.status == 200
                    
        except Exception:
            return False
