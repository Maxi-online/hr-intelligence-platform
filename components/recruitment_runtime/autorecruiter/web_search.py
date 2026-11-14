"""
AutoGPT Web Search Tool - Internet Search

Provides the AutoGPT agent with Internet access for:
- Searching for up-to-date information
- Trends studies
- Collection of company data
- Labour market analysis

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
    Internet search tool
    
    Opportunities:
    - Google Search API
    - Searching for news.
    - Searching for company information
    - Trends analysis
    """
    
    def __init__(self, google_api_key: str = None, search_engine_id: str = None):
        self.google_api_key = google_api_key or "demo_key"
        self.search_engine_id = search_engine_id or "demo_engine"
        
        # Basic URL for Search
        self.google_search_url = "https://www.googleapis.com/customsearch/v1"
        self.duckduckgo_url = "https://api.duckduckgo.com/"
        
        # Statistics
        self.search_stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0
        }
        
        logger.info('🌐 Web Search Tool initialized')
    
    async def search(self, query: str, num_results: int = 10, 
                    search_type: str = "general") -> List[Dict[str, Any]]:
        """
        Main search method
        
        Args:
            query: Search request
            num_results: Number of results
            search_type: Search type (general, news, companies, trends))
        """
        try:
            self.search_stats["total_searches"] += 1
            
            logger.info(f"🔍 Search: {query} (type: {search_type})")
            
            # Select search method
            if search_type == "news":
                results = await self._search_news(query, num_results)
            elif search_type == "companies":
                results = await self._search_companies(query, num_results)
            elif search_type == "trends":
                results = await self._search_trends(query, num_results)
            else:
                results = await self._general_search(query, num_results)
            
            self.search_stats["successful_searches"] += 1
            logger.info(f"✅ Found {len(results)} Results")
            
            return results
            
        except Exception as e:
            self.search_stats["failed_searches"] += 1
            logger.error(f"❌ Error of search: {e}")
            return []
    
    async def _general_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'Common Search Through Google Customs Search'
        try:
            # Try Google Community Search API.
            results = await self._google_search(query, num_results)
            
            if not results:
                # Fallback to DuckDuckGo
                results = await self._duckduckgo_search(query, num_results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ General Search Error: {e}")
            return self._create_mock_results(query, num_results)
    
    async def _google_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'Searching through Google Customs Search API'
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
                        logger.warning(f"Google Search API error: {response.status}")
                        return []
            
        except Exception as e:
            logger.error(f"❌ The Google Search Error: {e}")
            return []
    
    async def _duckduckgo_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'Alternative DuckDuckGo Search'
        try:
            # Simplified DuckDuckGo Request
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
            logger.error(f"❌ DuckDuckGo Search Error: {e}")
            return []
    
    async def _search_news(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'News Search'
        try:
            # Adding modifyors to search for news.
            news_query = f"{query} news recent 2024"
            
            # Using Google News Search
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
            logger.error(f"❌ Error in search of news: {e}")
            return self._create_mock_news(query, num_results)
    
    async def _search_companies(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'Searching for company information'
        try:
            # Specialized request for companies
            company_query = f"{query} company information about careers jobs"
            
            results = await self._google_search(company_query, num_results)
            
            if not results:
                results = self._create_mock_company_info(query, num_results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in search of companies: {e}")
            return self._create_mock_company_info(query, num_results)
    
    async def _search_trends(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'Searching for Trends'
        try:
            # Request for trend search
            trends_query = f"{query} trends 2024 statistics market analysis"
            
            results = await self._google_search(trends_query, num_results)
            
            if not results:
                results = self._create_mock_trends(query, num_results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Errors in search of trends: {e}")
            return self._create_mock_trends(query, num_results)
    
    def _parse_google_results(self, data: Dict[str, Any], result_type: str = "general") -> List[Dict[str, Any]]:
        'Parsing Google Search Results'
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
                
                # Additional News Fields
                if result_type == "news" and "pagemap" in item:
                    pagemap = item["pagemap"]
                    if "metatags" in pagemap and pagemap["metatags"]:
                        metatag = pagemap["metatags"][0]
                        result["published_date"] = metatag.get("article:published_time", "")
                        result["author"] = metatag.get("author", "")
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Errors of Google Parsing Results: {e}")
            return []
    
    def _parse_duckduckgo_results(self, data: Dict[str, Any], num_results: int) -> List[Dict[str, Any]]:
        'DuckDuckGo Results Parsing'
        try:
            results = []
            
            # DuckDuckGo returns different types of results
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
            logger.error(f"❌ DuckDuckGo Results Parsing Error: {e}")
            return []
    
    def _create_mock_results(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'Creating a lock result when API is not available'
        mock_results = []
        
        for i in range(min(num_results, 5)):
            result = {
                "title": f"Result {i+1} For a request.{query}'",
                "link": f"https://example.com/result-{i+1}",
                "snippet": f"It's a lock result.{i+1} To demonstrate search work. Request: {query}",
                "source": "mock",
                "type": "general",
                "found_at": datetime.now().isoformat(),
                "_note": 'Lock result - real API not available'
            }
            mock_results.append(result)
        
        return mock_results
    
    def _create_mock_news(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'Making a Lock News'
        mock_news = []
        
        news_topics = [
            'Training in IT Revolving 2024',
            'New recruitment technologies',
            'Labour market developments',
            'AI in recruitment',
            'Remote work and recruitment'
        ]
        
        for i, topic in enumerate(news_topics[:num_results]):
            news = {
                "title": f"{topic} - {query}",
                "link": f"https://news-example.com/article-{i+1}",
                "snippet": f"The latest news about {topic.lower()}. Analysis and trends {query}.",
                "source": "mock_news",
                "type": "news",
                "published_date": datetime.now().isoformat(),
                "author": "News Reporter",
                "found_at": datetime.now().isoformat(),
                "_note": 'Mock News - Real API not available'
            }
            mock_news.append(news)
        
        return mock_news
    
    def _create_mock_company_info(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'Creating company-related information'
        mock_companies = []
        
        for i in range(min(num_results, 3)):
            company = {
                "title": f"Company {query} - Official website",
                "link": f"https://{query.lower().replace(' ', '')}-company.com",
                "snippet": f"Official company information {query}. Vacancies, career, company.",
                "source": "mock_company",
                "type": "company",
                "company_size": '1000+ staff',
                "industry": 'IT and technology',
                "found_at": datetime.now().isoformat(),
                "_note": 'Mock company information'
            }
            mock_companies.append(company)
        
        return mock_companies
    
    def _create_mock_trends(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        'Creating Mock Trends'
        mock_trends = []
        
        trend_topics = [
            'Increased demand for specialists',
            'New technologies in the field of',
            'Wage changes',
            'Popular skills',
            'Development projections'
        ]
        
        for i, trend in enumerate(trend_topics[:num_results]):
            trend_result = {
                "title": f"{trend} - {query} 2024",
                "link": f"https://trends-example.com/trend-{i+1}",
                "snippet": f"Trends analysis: {trend.lower()} in the field of human rights {query}. Statistics and projections.",
                "source": "mock_trends",
                "type": "trends",
                "trend_direction": 'growth' if i % 2 == 0 else 'stability',
                "found_at": datetime.now().isoformat(),
                "_note": 'Mock trend - real API not available'
            }
            mock_trends.append(trend_result)
        
        return mock_trends
    
    async def search_specific_site(self, query: str, site: str, num_results: int = 5) -> List[Dict[str, Any]]:
        'Search on a specific site'
        try:
            site_query = f"site:{site} {query}"
            return await self._general_search(site_query, num_results)
            
        except Exception as e:
            logger.error(f"❌ Error in search on the site {site}: {e}")
            return []
    
    async def search_hh_vacancies(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        'Search for vacancies on HeadHunter'
        return await self.search_specific_site(query, "hh.ru", num_results)
    
    async def search_habr_articles(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        'Search for Habr articles'
        return await self.search_specific_site(query, "habr.com", num_results)
    
    def get_search_stats(self) -> Dict[str, Any]:
        'Search statistics'
        return {
            **self.search_stats,
            "success_rate": (
                self.search_stats["successful_searches"] / max(self.search_stats["total_searches"], 1)
            ) * 100
        }
    
    async def verify_url_accessibility(self, url: str) -> bool:
        'URL accessibility check'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=10) as response:
                    return response.status == 200
                    
        except Exception:
            return False
