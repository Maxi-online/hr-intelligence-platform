"""
Инициализация централизованной базы данных PostgreSQL
Создает таблицы и заполняет их базовыми данными
"""
import os

import psycopg2
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def init_database():
    """Инициализация базы данных"""
    
    # Конфигурация подключения
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'office_services_user',
        'password': os.environ["SERVICES_CENTRAL_POSTGRES_ENVIRONMENT_POSTGRES_PASSWORD"],
        'database': 'office_services_agents'
    }
    
    try:
        # Подключение к PostgreSQL
        connection = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        
        cursor = connection.cursor()
        
        # Создание таблиц
        logger.info("📋 Создание таблиц...")
        
        # Таблица конфигураций агентов
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_configurations (
            agent_id VARCHAR(255) PRIMARY KEY,
            agent_name VARCHAR(255) NOT NULL,
            role VARCHAR(255) NOT NULL,
            persona TEXT,
            system_prompt TEXT,
            tools JSONB,
            rules JSONB,
            tone_of_voice TEXT,
            training_data JSONB,
            routing_rules JSONB,
            version VARCHAR(50) DEFAULT '1.0.0',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Таблица организационной структуры
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS organizational_structure (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            department VARCHAR(255),
            division VARCHAR(255),
            position VARCHAR(255),
            full_name VARCHAR(255),
            hierarchy_level INTEGER,
            manager_id UUID,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Реестр развернутых агентов
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS deployed_agents_registry (
            agent_id VARCHAR(255) PRIMARY KEY,
            teams_identity VARCHAR(255),
            channel_roles JSONB,
            status VARCHAR(50) DEFAULT 'active',
            limits JSONB,
            last_activity TIMESTAMP,
            performance_metrics JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id)
        );
        """)
        
        # Таблица оперативной памяти
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS operational_memory (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            agent_id VARCHAR(255),
            session_id VARCHAR(255),
            task_context TEXT,
            user_id VARCHAR(255),
            message_history JSONB,
            current_focus TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id)
        );
        """)
        
        # Таблица core памяти
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS core_memory (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            agent_id VARCHAR(255),
            rule_type VARCHAR(100),
            rule_content TEXT,
            priority INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id)
        );
        """)
        
        # Таблица истории чатов
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            agent_id VARCHAR(255),
            user_id VARCHAR(255),
            role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            session_id VARCHAR(255),
            metadata JSONB DEFAULT '{}',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id)
        );
        """)
        
        # Таблица системных метрик
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_metrics (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            metric_name VARCHAR(255),
            metric_value DECIMAL(10,2),
            agent_id VARCHAR(255),
            period VARCHAR(50),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id)
        );
        """)
        
        # Создание индексов
        logger.info("📊 Создание индексов...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_agent_config_active ON agent_configurations (is_active);",
            "CREATE INDEX IF NOT EXISTS idx_deployed_agents_status ON deployed_agents_registry (status);",
            "CREATE INDEX IF NOT EXISTS idx_chat_history_agent_time ON chat_history (agent_id, timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_operational_memory_agent ON operational_memory (agent_id);",
            "CREATE INDEX IF NOT EXISTS idx_department ON organizational_structure (department);",
            "CREATE INDEX IF NOT EXISTS idx_hierarchy ON organizational_structure (hierarchy_level);",
            "CREATE INDEX IF NOT EXISTS idx_agent_rule_type ON core_memory (agent_id, rule_type);",
            "CREATE INDEX IF NOT EXISTS idx_priority ON core_memory (priority);",
            "CREATE INDEX IF NOT EXISTS idx_agent_user ON chat_history (agent_id, user_id);",
            "CREATE INDEX IF NOT EXISTS idx_session ON chat_history (session_id);",
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON chat_history (timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_metric_name ON system_metrics (metric_name);",
            "CREATE INDEX IF NOT EXISTS idx_agent_metric ON system_metrics (agent_id, metric_name);",
            "CREATE INDEX IF NOT EXISTS idx_period ON system_metrics (period);"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # Логирование инициализации
        cursor.execute("""
        INSERT INTO system_metrics (metric_name, metric_value, agent_id, period) 
        VALUES ('database_initialized', 1.0, 'system', 'initialization');
        """)
        
        connection.commit()
        logger.info("✅ База данных успешно инициализирована")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    init_database()
