"""
ClickHouse Database Manager for Candidate Analysis System
Optimized to maximize the productivity of analytical queries
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

# Add the parent directory to the route to import the used modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import (
    Candidate, CandidateProfile, DatabaseCandidate,
    SkillAnalysis, AIAnalysisResponse
)
from shared.utils import load_config

logger = logging.getLogger("clickhouse-manager")

class ClickHouseManager:
    'High-performance Clickhouse manager for HR data'
    
    def __init__(self):
        self.config = load_config()
        self.ch_config = self.config.get("clickhouse", {})
        
        # ClickHouse connectivity options
        self.host = self.ch_config.get("host", "clickhouse")
        self.port = self.ch_config.get("port", 9000)
        self.http_port = self.ch_config.get("http_port", 8123)
        self.database = self.ch_config.get("database", "hrhelp")
        self.username = self.ch_config.get("username", "hrhelp_user")
        self.password = self.ch_config.get("password", "")
        
        # Initialization of customers
        self._init_clients()
        self._init_schema()
        
        logger.info(f"✅ ClickHouse Manager initialized for {self.host}:{self.port}")

    def _init_clients(self):
        'Customer Initialization ClickHouse'
        try:
            # Native TCP client (better for bulk operations)
            self.native_client = ClickHouseClient(
                host=self.host,
                port=self.port,
                database='default',  # Use the default base for initialization
                user=self.username,
                password=self.password,
                secure=False,
                compression=True,
                settings={
                    'max_memory_usage': '10000000000',  # 10GB
                    'max_threads': '8',
                    'max_execution_time': '300',  # 5 minutes
                    'send_timeout': '300',
                    'receive_timeout': '300',
                }
            )
            
            # SYSTEM CORRECTION: HTTP client will create after database development
            # To avoid initialization errors
            self.http_client = None
            
            # Checking the connection
            version = self.native_client.execute("SELECT version()")[0][0]
            logger.info(f"🚀 Connecting to ClickHouse {version} Established")
            
        except Exception as e:
            logger.error(f"❌ Connection error to ClickHouse: {e}")
            raise

    def _init_schema(self):
        'Initialization of a database scheme'
        try:
            logger.info(f"🏗️ Database development {self.database}...")
            self.native_client.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            logger.info(f"✅ Database {self.database} created or already in existence")
            
            # SYSTEMIC CORRIGENDUM: Switching to the correct database
            self._reconnect_to_database()
            
            # Read and execute SQL from the diagram file
            schema_path = os.path.join("config", "clickhouse", "init_schema.sql")
            if os.path.exists(schema_path):
                logger.info(f"📄 Implementation of the scheme from {schema_path}...")
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                # Disaggregated by individual requests and executed
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                executed_count = 0
                for statement in statements:
                    if statement and not statement.startswith('--'):
                        try:
                            self.native_client.execute(statement)
                            executed_count += 1
                        except Exception as e:
                            if "already exists" not in str(e).lower():
                                logger.warning(f"SQL warning: {e}")
                
                logger.info(f"✅ ClickHouse is initialized - implemented {executed_count} Requests")
            else:
                logger.warning('⚠️ Schematic file not found, basic tables created...')
                self._create_basic_tables()
                
        except Exception as e:
            logger.error(f"❌ Error in initializing the scheme: {e}")
            self._create_basic_tables()

    def _reconnect_to_database(self):
        'Reconnecting to a target database after its creation'
        try:
            logger.info(f"🔄 Reconnecting to the database {self.database}...")
            
            # Close the old connections.
            if hasattr(self, 'native_client'):
                self.native_client.disconnect()
            if hasattr(self, 'http_client') and self.http_client:
                self.http_client.close()
            
            # Create new links to the target database
            self.native_client = ClickHouseClient(
                host=self.host,
                port=self.port,
                database=self.database,  # Now let's connect to hrhelp.
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
            
            # SYSTEM CORRIGENDUM: Now create a HTTP client after the creation of an database
            self.http_client = clickhouse_connect.get_client(
                host=self.host,
                port=self.http_port,
                database=self.database,  # Now let's connect to hrhelp.
                username=self.username,
                password=self.password,
                secure=False,
                compress=True,
                settings={
                    'max_memory_usage': '10000000000',
                    'max_execution_time': '300',
                }
            )
            logger.info('✅ HTTP Clickhouse client created and connected to the database')
            
            # Check that the reconnect is successful.
            test_query = self.native_client.execute("SELECT 1")[0][0]
            if test_query == 1:
                logger.info(f"✅ Base connection {self.database} successful")
            
        except Exception as e:
            logger.error(f"❌ Error of switching to the database: {e}")
            raise

    def _create_basic_tables(self):
        'Create basic tables if diagram file is not available'
        try:
            logger.info('🏗️ Establishment of baseline tables...')
            
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
            logger.info('✅ Base tables established')
            
        except Exception as e:
            logger.error(f"❌ Error in creating basic tables: {e}")
            raise

    @contextmanager
    def get_connection(self, use_http=False):
        'Context manager for connection'
        client = self.http_client if use_http else self.native_client
        try:
            yield client
        except Exception as e:
            logger.error(f"❌ Error in Request: {e}")
            raise
        finally:
            # Clickhouse clients control connections automatically
            pass

    def save_candidate(self, candidate: Candidate, ai_analysis: Optional[AIAnalysisResponse] = None) -> bool:
        """
        Maintaining a candidate on ClickHouse with maximum productivity
        """
        try:
            start_time = time.time()
            
            # Preparation of the candidate &apos; s data
            candidate_data = self._prepare_candidate_data(candidate, ai_analysis)
            
            # We're going to use PRELACE for upsert operation.
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
            
            # Save AI analysis if available
            if ai_analysis:
                self._save_ai_analysis(candidate.id, ai_analysis)
            
            elapsed = time.time() - start_time
            logger.debug(f"💾 Candidature {candidate.id} retained for {elapsed:.3f}c")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error of preservation of the candidate {candidate.id}: {e}")
            return False

    def _prepare_candidate_data(self, candidate: Candidate, ai_analysis: Optional[AIAnalysisResponse] = None) -> tuple:
        'Preparation of the candidate &apos; s data for the ClickHouse'
        
        # Data extraction with None values processing
        area_name = candidate.area.get('name', '') if candidate.area else ''
        experience_level = self._extract_experience_level(candidate.experience)
        
        # Salary processing
        salary_from = None
        salary_to = None
        if candidate.salary:
            salary_from = candidate.salary.get('from')
            salary_to = candidate.salary.get('to')
        
        # AI Status
        ai_status = 'completed' if ai_analysis else 'pending'
        
        return (
            candidate.id,
            candidate.id,  # hh_id same as id
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
        'Extraction of experience from the object experience'
        if not experience:
            return 'unknown'
        
        # Trying to get out of different fields
        if isinstance(experience, dict):
            return experience.get('level', experience.get('experience', 'unknown'))
        return str(experience)

    def _save_ai_analysis(self, candidate_id: str, ai_analysis: AIAnalysisResponse):
        'Maintenance of AI analysis in selected tables'
        try:
            # Maintaining common speeds
            with self.get_connection() as client:
                # Main evaluation
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
                        "general",  # search_query can be made more specific
                        ai_analysis.overall_score,
                        ai_analysis.analysis_summary,
                        int(ai_analysis.processing_time * 1000),  # in milliseconds
                        ai_analysis.keyword_relevance_score or 0.0,
                        ai_analysis.filter_match_score or 0.0,
                        ai_analysis.recency_score or 0.0,
                        ai_analysis.profile_completeness_score or 0.0,
                        ai_analysis.reasoning or '',
                        datetime.now(timezone.utc)
                    )]
                )
                
                # Skills analysis
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
            
            logger.debug(f"💡 AI Analysis for the candidate {candidate_id} retained")
            
        except Exception as e:
            logger.error(f"❌ Mistake of AI analysis: {e}")

    def get_candidate(self, candidate_id: str) -> Optional[DatabaseCandidate]:
        'High-productivity ID candidate received'
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
            logger.error(f"❌ Error of receiving the candidate {candidate_id}: {e}")
            return None

    def search_candidates(self, search_params: Dict[str, Any], limit: int = 100) -> List[DatabaseCandidate]:
        """
        High-quality search using ClickHouse Optimization
        """
        try:
            start_time = time.time()
            
            # Creating WHERE Conditions
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
            
            # Basic request
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
                logger.info(f"🔍 Found {len(candidates)} candidates for election to the {elapsed:.3f}c")
                
                return candidates
                
        except Exception as e:
            logger.error(f"❌ Error in search of candidates: {e}")
            return []

    def _row_to_database_candidate(self, row: tuple, column_names: List[str]) -> Optional[DatabaseCandidate]:
        'ClickHouse in DatabaseCandidate'
        try:
            # Create a dictionary from a string
            row_dict = dict(zip(column_names, row))
            
            # Create Candidate from Data
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
            
            # Create Candidate Profile
            profile = CandidateProfile(
                id=candidate.id,
                hh_data=candidate,
                skill_analysis=[],
                overall_ai_score=0.0,
                last_analyzed=None,
                analysis_status=row_dict.get('ai_analysis_status', 'pending')
            )
            
            # DatabaseCandidate
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
            logger.error(f"❌ Conversion error in DatabaseCandidate: {e}")
            return None

    def update_search_count(self, candidate_id: str):
        'Update of search counter (high performance operation))'
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
            
            logger.debug(f"📊 Search counter for {candidate_id} updated")
            
        except Exception as e:
            logger.error(f"❌ Error of update of the search calculator: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        "Getting statistics using Clickhouse's analytical power"
        try:
            with self.get_connection(use_http=True) as client:
                # Simple basic statistics
                total_candidates = client.query(f"SELECT count() FROM {self.database}.candidates").result_rows[0][0]
                
                analyzed_candidates = 0
                if total_candidates > 0:
                    analyzed_candidates = client.query(f"""
                        SELECT countIf(ai_analysis_status = 'completed') 
                        FROM {self.database}.candidates
                    """).result_rows[0][0]
                
                # Safe calculation of interest
                analysis_coverage = 0.0
                if total_candidates > 0:
                    analysis_coverage = round((analyzed_candidates / total_candidates) * 100, 2)
                
                stats = {
                    "total_candidates": int(total_candidates),
                    "analyzed_candidates": int(analyzed_candidates), 
                    "analysis_coverage_percent": float(analysis_coverage),
                    "database_type": "ClickHouse"
                }
            
            logger.info('📊 Clickhouse statistics received')
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error in obtaining statistics: {e}")
            return {
                "total_candidates": 0,
                "analyzed_candidates": 0,
                "analysis_coverage_percent": 0.0,
                "database_type": "ClickHouse",
                "error": str(e)
            }

    def get_top_candidates(self, limit: int = 10) -> List[DatabaseCandidate]:
        'To receive the top of the search engine candidates'
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
            logger.error(f"❌ Error in getting top candidates: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        'ClickHouse Health Check'
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
        'Closure of compounds'
        try:
            if hasattr(self, 'native_client'):
                self.native_client.disconnect()
            if hasattr(self, 'http_client'):
                self.http_client.close()
            logger.info('🔌 Clickhouse connections closed')
        except Exception as e:
            logger.error(f"❌ Mistake of closing connections: {e}")