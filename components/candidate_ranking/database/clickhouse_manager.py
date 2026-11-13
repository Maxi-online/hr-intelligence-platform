"""
ClickHouse Database Manager для Candidate Analysis системы
Оптимизирован для максимальной производительности аналитических запросов
"""

import clickhouse_connect
from clickhouse_driver import Client as ClickHouseClient
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
import logging
from contextlib import contextmanager
import time

# Добавляем родительскую директорию в путь для импорта shared модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    Candidate, CandidateProfile, DatabaseCandidate,
    SkillAnalysis, AIAnalysisResponse
)
from shared.utils import load_config

logger = logging.getLogger("clickhouse-manager")

class ClickHouseManager:
    """Высокопроизводительный менеджер ClickHouse для HR данных"""
    
    def __init__(self):
        self.config = load_config()
        self.ch_config = self.config.get("clickhouse", {})
        
        # Параметры подключения ClickHouse
        self.host = self.ch_config.get("host", "clickhouse")
        self.port = self.ch_config.get("port", 9000)
        self.http_port = self.ch_config.get("http_port", 8123)
        self.database = self.ch_config.get("database", "hrhelp")
        self.username = self.ch_config.get("username", "hrhelp_user")
        self.password = self.ch_config.get("password", "")
        
        # Инициализация клиентов
        self._init_clients()
        self._init_schema()
        
        logger.info(f"✅ ClickHouse Manager инициализирован для {self.host}:{self.port}")

    def _init_clients(self):
        """Инициализация клиентов ClickHouse"""
        try:
            # Native TCP client (лучше для bulk операций)
            self.native_client = ClickHouseClient(
                host=self.host,
                port=self.port,
                database='default',  # Используем базу по умолчанию для инициализации
                user=self.username,
                password=self.password,
                secure=False,
                compression=True,
                settings={
                    'max_memory_usage': '10000000000',  # 10GB
                    'max_threads': '8',
                    'max_execution_time': '300',  # 5 минут
                    'send_timeout': '300',
                    'receive_timeout': '300',
                }
            )
            
            # СИСТЕМНОЕ ИСПРАВЛЕНИЕ: HTTP клиент создадим ПОСЛЕ создания базы данных
            # чтобы избежать ошибки инициализации
            self.http_client = None
            
            # Проверка подключения
            version = self.native_client.execute("SELECT version()")[0][0]
            logger.info(f"🚀 Подключение к ClickHouse {version} установлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к ClickHouse: {e}")
            raise

    def _init_schema(self):
        """Инициализация схемы базы данных"""
        try:
            logger.info(f"🏗️ Создание базы данных {self.database}...")
            self.native_client.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            logger.info(f"✅ База данных {self.database} создана или уже существует")
            
            # СИСТЕМНОЕ ИСПРАВЛЕНИЕ: Переподключение к правильной базе данных
            self._reconnect_to_database()
            
            # Читаем и выполняем SQL из файла схемы
            schema_path = os.path.join("config", "clickhouse", "init_schema.sql")
            if os.path.exists(schema_path):
                logger.info(f"📄 Выполнение схемы из {schema_path}...")
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                # Разбиваем на отдельные запросы и выполняем
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                executed_count = 0
                for statement in statements:
                    if statement and not statement.startswith('--'):
                        try:
                            self.native_client.execute(statement)
                            executed_count += 1
                        except Exception as e:
                            if "already exists" not in str(e).lower():
                                logger.warning(f"Предупреждение при выполнении SQL: {e}")
                
                logger.info(f"✅ Схема ClickHouse инициализирована - выполнено {executed_count} запросов")
            else:
                logger.warning("⚠️ Файл схемы не найден, создание базовых таблиц...")
                self._create_basic_tables()
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации схемы: {e}")
            self._create_basic_tables()

    def _reconnect_to_database(self):
        """Переподключение к целевой базе данных после её создания"""
        try:
            logger.info(f"🔄 Переподключение к базе данных {self.database}...")
            
            # Закрываем старые соединения
            if hasattr(self, 'native_client'):
                self.native_client.disconnect()
            if hasattr(self, 'http_client') and self.http_client:
                self.http_client.close()
            
            # Создаем новые соединения к целевой базе данных
            self.native_client = ClickHouseClient(
                host=self.host,
                port=self.port,
                database=self.database,  # Теперь подключаемся к hrhelp
                user=self.username,
                password=self.password,
                secure=False,
                compression=True,
                settings={
                    'max_memory_usage': '10000000000',
                    'max_threads': '8',
                    'max_execution_time': '300',
                    'send_timeout': '300',
                    'receive_timeout': '300',
                }
            )
            
            # СИСТЕМНОЕ ИСПРАВЛЕНИЕ: Теперь создаем HTTP клиент после создания БД
            self.http_client = clickhouse_connect.get_client(
                host=self.host,
                port=self.http_port,
                database=self.database,  # Теперь подключаемся к hrhelp
                username=self.username,
                password=self.password,
                secure=False,
                compress=True,
                settings={
                    'max_memory_usage': '10000000000',
                    'max_execution_time': '300',
                }
            )
            logger.info("✅ HTTP клиент ClickHouse создан и подключен к базе данных")
            
            # Проверяем что переподключение успешно
            test_query = self.native_client.execute("SELECT 1")[0][0]
            if test_query == 1:
                logger.info(f"✅ Переподключение к базе {self.database} выполнено успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка переподключения к базе данных: {e}")
            raise

    def _create_basic_tables(self):
        """Создание базовых таблиц если файл схемы недоступен"""
        try:
            logger.info("🏗️ Создание базовых таблиц...")
            
            basic_candidates_table = f"""
            CREATE TABLE IF NOT EXISTS {self.database}.candidates (
                id String,
                hh_id String,
                name LowCardinality(String),
                title String,
                age UInt8,
                area_name LowCardinality(String),
                experience_level LowCardinality(String),
                salary_from Nullable(UInt32),
                salary_to Nullable(UInt32),
                skills Array(String),
                updated_at DateTime64(3),
                created_at DateTime64(3) DEFAULT now64(),
                search_count UInt32 DEFAULT 0,
                ai_analysis_status LowCardinality(String) DEFAULT 'pending'
            )
            ENGINE = MergeTree()
            PARTITION BY toYYYYMM(created_at)
            ORDER BY (area_name, experience_level, created_at, id)
            SETTINGS index_granularity = 8192
            """
            
            self.native_client.execute(basic_candidates_table)
            logger.info("✅ Базовые таблицы созданы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания базовых таблиц: {e}")
            raise

    @contextmanager
    def get_connection(self, use_http=False):
        """Контекстный менеджер для получения соединения"""
        client = self.http_client if use_http else self.native_client
        try:
            yield client
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения запроса: {e}")
            raise
        finally:
            # ClickHouse клиенты управляют соединениями автоматически
            pass

    def save_candidate(self, candidate: Candidate, ai_analysis: Optional[AIAnalysisResponse] = None) -> bool:
        """
        Сохранение кандидата в ClickHouse с максимальной производительностью
        """
        try:
            start_time = time.time()
            
            # Подготовка данных кандидата
            candidate_data = self._prepare_candidate_data(candidate, ai_analysis)
            
            # Используем REPLACE для upsert операции
            with self.get_connection() as client:
                client.execute(
                    f"""
                    INSERT INTO {self.database}.candidates 
                    (id, hh_id, name, title, age, area_name, experience_level, 
                     salary_from, salary_to, skills, updated_at, created_at, 
                     search_count, ai_analysis_status) 
                    VALUES
                    """,
                    [candidate_data]
                )
            
            # Сохранение AI анализа если есть
            if ai_analysis:
                self._save_ai_analysis(candidate.id, ai_analysis)
            
            elapsed = time.time() - start_time
            logger.debug(f"💾 Кандидат {candidate.id} сохранен за {elapsed:.3f}с")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения кандидата {candidate.id}: {e}")
            return False

    def _prepare_candidate_data(self, candidate: Candidate, ai_analysis: Optional[AIAnalysisResponse] = None) -> tuple:
        """Подготовка данных кандидата для вставки в ClickHouse"""
        
        # Извлечение данных с обработкой None значений
        area_name = candidate.area.get('name', '') if candidate.area else ''
        experience_level = self._extract_experience_level(candidate.experience)
        
        # Обработка зарплаты
        salary_from = None
        salary_to = None
        if candidate.salary:
            salary_from = candidate.salary.get('from')
            salary_to = candidate.salary.get('to')
        
        # AI статус
        ai_status = 'completed' if ai_analysis else 'pending'
        
        return (
            candidate.id,
            candidate.id,  # hh_id то же что и id
            candidate.name or '',
            candidate.title or '',
            candidate.age or 0,
            area_name,
            experience_level,
            salary_from,
            salary_to,
            candidate.skills or [],
            candidate.updated_at,
            datetime.now(timezone.utc),
            0,  # search_count
            ai_status
        )

    def _extract_experience_level(self, experience: Dict[str, Any]) -> str:
        """Извлечение уровня опыта из объекта experience"""
        if not experience:
            return 'unknown'
        
        # Попытка извлечь из различных полей
        if isinstance(experience, dict):
            return experience.get('level', experience.get('experience', 'unknown'))
        return str(experience)

    def _save_ai_analysis(self, candidate_id: str, ai_analysis: AIAnalysisResponse):
        """Сохранение AI анализа в отдельные таблицы"""
        try:
            # Сохранение общих скоров
            with self.get_connection() as client:
                # Основная оценка
                client.execute(
                    f"""
                    INSERT INTO {self.database}.ai_candidate_scores 
                    (candidate_id, search_query, overall_score, analysis_summary, 
                     processing_time_ms, keyword_relevance_score, filter_match_score,
                     recency_score, profile_completeness_score, reasoning, created_at) 
                    VALUES
                    """,
                    [(
                        candidate_id,
                        "general",  # search_query можно сделать более специфичным
                        ai_analysis.overall_score,
                        ai_analysis.analysis_summary,
                        int(ai_analysis.processing_time * 1000),  # в миллисекундах
                        ai_analysis.keyword_relevance_score or 0.0,
                        ai_analysis.filter_match_score or 0.0,
                        ai_analysis.recency_score or 0.0,
                        ai_analysis.profile_completeness_score or 0.0,
                        ai_analysis.reasoning or '',
                        datetime.now(timezone.utc)
                    )]
                )
                
                # Анализ навыков
                if ai_analysis.skill_analysis:
                    skill_data = []
                    for skill in ai_analysis.skill_analysis:
                        skill_data.append((
                            candidate_id,
                            skill.skill_name,
                            skill.relevance_score,
                            skill.proficiency_level,
                            skill.years_experience,
                            skill.ai_confidence,
                            "general",  # search_query
                            skill.analysis_timestamp or datetime.now(timezone.utc)
                        ))
                    
                    if skill_data:
                        client.execute(
                            f"""
                            INSERT INTO {self.database}.ai_skill_analysis 
                            (candidate_id, skill_name, relevance_score, proficiency_level,
                             years_experience, ai_confidence, search_query, analysis_timestamp) 
                            VALUES
                            """,
                            skill_data
                        )
            
            logger.debug(f"💡 AI анализ для кандидата {candidate_id} сохранен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения AI анализа: {e}")

    def get_candidate(self, candidate_id: str) -> Optional[DatabaseCandidate]:
        """Получение кандидата по ID с высокой производительностью"""
        try:
            with self.get_connection(use_http=True) as client:
                result = client.query(
                    f"""
                    SELECT * FROM {self.database}.candidates 
                    WHERE id = %(candidate_id)s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                    """,
                    parameters={"candidate_id": candidate_id}
                )
                
                if result.result_rows:
                    row = result.result_rows[0]
                    return self._row_to_database_candidate(row, result.column_names)
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения кандидата {candidate_id}: {e}")
            return None

    def search_candidates(self, search_params: Dict[str, Any], limit: int = 100) -> List[DatabaseCandidate]:
        """
        Высокопроизводительный поиск кандидатов с использованием ClickHouse оптимизаций
        """
        try:
            start_time = time.time()
            
            # Построение WHERE условий
            where_conditions = []
            params = {}
            
            if search_params.get("text"):
                where_conditions.append("(title LIKE %(text_pattern)s OR arrayExists(x -> x LIKE %(text_pattern)s, skills))")
                params["text_pattern"] = f"%{search_params['text']}%"
            
            if search_params.get("area_name"):
                where_conditions.append("area_name = %(area_name)s")
                params["area_name"] = search_params["area_name"]
            
            if search_params.get("experience_level"):
                where_conditions.append("experience_level = %(experience_level)s")
                params["experience_level"] = search_params["experience_level"]
            
            if search_params.get("salary_from"):
                where_conditions.append("(salary_from >= %(salary_from)s OR salary_to >= %(salary_from)s)")
                params["salary_from"] = search_params["salary_from"]
            
            if search_params.get("skills"):
                skills = search_params["skills"]
                if isinstance(skills, list):
                    where_conditions.append("hasAny(skills, %(required_skills)s)")
                    params["required_skills"] = skills
            
            # Базовый запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            query = f"""
            SELECT * FROM {self.database}.candidates 
            WHERE {where_clause}
            ORDER BY created_at DESC, search_count DESC
            LIMIT %(limit)s
            """
            params["limit"] = limit
            
            with self.get_connection(use_http=True) as client:
                result = client.query(query, parameters=params)
                
                candidates = []
                for row in result.result_rows:
                    candidate = self._row_to_database_candidate(row, result.column_names)
                    if candidate:
                        candidates.append(candidate)
                
                elapsed = time.time() - start_time
                logger.info(f"🔍 Найдено {len(candidates)} кандидатов за {elapsed:.3f}с")
                
                return candidates
                
        except Exception as e:
            logger.error(f"❌ Ошибка поиска кандидатов: {e}")
            return []

    def _row_to_database_candidate(self, row: tuple, column_names: List[str]) -> Optional[DatabaseCandidate]:
        """Конвертация строки ClickHouse в DatabaseCandidate"""
        try:
            # Создание словаря из строки
            row_dict = dict(zip(column_names, row))
            
            # Создание объекта Candidate из данных
            candidate = Candidate(
                id=row_dict.get('id', ''),
                name=row_dict.get('name'),
                title=row_dict.get('title', ''),
                age=row_dict.get('age'),
                area={'name': row_dict.get('area_name', '')},
                experience={'level': row_dict.get('experience_level', '')},
                salary={
                    'from': row_dict.get('salary_from'),
                    'to': row_dict.get('salary_to'),
                } if row_dict.get('salary_from') or row_dict.get('salary_to') else None,
                skills=row_dict.get('skills', []),
                verified_skills=[],
                updated_at=row_dict.get('updated_at', datetime.now(timezone.utc)),
                url='',
                photo_url=None,
                has_cover_letter=False,
                score=0.0
            )
            
            # Создание CandidateProfile
            profile = CandidateProfile(
                id=candidate.id,
                hh_data=candidate,
                skill_analysis=[],
                overall_ai_score=0.0,
                last_analyzed=None,
                analysis_status=row_dict.get('ai_analysis_status', 'pending')
            )
            
            # Создание DatabaseCandidate
            db_candidate = DatabaseCandidate(
                id=candidate.id,
                profile=profile,
                created_at=row_dict.get('created_at', datetime.now(timezone.utc)),
                updated_at=row_dict.get('updated_at', datetime.now(timezone.utc)),
                search_count=row_dict.get('search_count', 0),
                last_searched=None
            )
            
            return db_candidate
            
        except Exception as e:
            logger.error(f"❌ Ошибка конвертации строки в DatabaseCandidate: {e}")
            return None

    def update_search_count(self, candidate_id: str):
        """Обновление счетчика поисков (высокопроизводительная операция)"""
        try:
            with self.get_connection() as client:
                client.execute(
                    f"""
                    ALTER TABLE {self.database}.candidates 
                    UPDATE search_count = search_count + 1 
                    WHERE id = %(candidate_id)s
                    """,
                    {"candidate_id": candidate_id}
                )
            
            logger.debug(f"📊 Счетчик поисков для {candidate_id} обновлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления счетчика поисков: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики с использованием аналитической мощи ClickHouse"""
        try:
            with self.get_connection(use_http=True) as client:
                # Простая базовая статистика
                total_candidates = client.query(f"SELECT count() FROM {self.database}.candidates").result_rows[0][0]
                
                analyzed_candidates = 0
                if total_candidates > 0:
                    analyzed_candidates = client.query(f"""
                        SELECT countIf(ai_analysis_status = 'completed') 
                        FROM {self.database}.candidates
                    """).result_rows[0][0]
                
                # Безопасный расчет процента
                analysis_coverage = 0.0
                if total_candidates > 0:
                    analysis_coverage = round((analyzed_candidates / total_candidates) * 100, 2)
                
                stats = {
                    "total_candidates": int(total_candidates),
                    "analyzed_candidates": int(analyzed_candidates), 
                    "analysis_coverage_percent": float(analysis_coverage),
                    "database_type": "ClickHouse"
                }
            
            logger.info("📊 Статистика ClickHouse получена")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {
                "total_candidates": 0,
                "analyzed_candidates": 0,
                "analysis_coverage_percent": 0.0,
                "database_type": "ClickHouse",
                "error": str(e)
            }

    def get_top_candidates(self, limit: int = 10) -> List[DatabaseCandidate]:
        """Получение топ кандидатов по поисковой активности"""
        try:
            with self.get_connection(use_http=True) as client:
                result = client.query(
                    f"""
                    SELECT * FROM {self.database}.candidates 
                    ORDER BY search_count DESC, created_at DESC 
                    LIMIT %(limit)s
                    """,
                    parameters={"limit": limit}
                )
                
                candidates = []
                for row in result.result_rows:
                    candidate = self._row_to_database_candidate(row, result.column_names)
                    if candidate:
                        candidates.append(candidate)
                
                return candidates
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения топ кандидатов: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья ClickHouse соединения"""
        try:
            with self.get_connection(use_http=True) as client:
                version = client.query("SELECT version()").result_rows[0][0]
                uptime = client.query("SELECT uptime()").result_rows[0][0]
                
                return {
                    "status": "healthy",
                    "database_type": "ClickHouse",
                    "version": version,
                    "uptime_seconds": uptime,
                    "host": self.host,
                    "database": self.database
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_type": "ClickHouse"
            }

    def close(self):
        """Закрытие соединений"""
        try:
            if hasattr(self, 'native_client'):
                self.native_client.disconnect()
            if hasattr(self, 'http_client'):
                self.http_client.close()
            logger.info("🔌 ClickHouse соединения закрыты")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия соединений: {e}")