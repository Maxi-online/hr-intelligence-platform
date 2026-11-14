-- ====================================
-- Central database of agents
-- SQL "fingerprints" of agents according to diagram
-- ====================================

-- Database development
CREATE DATABASE IF NOT EXISTS office_services_agents;

USE office_services_agents;

-- ====================================
-- Agent configuration table
-- ====================================
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ====================================
-- Organization chart
-- ====================================
CREATE TABLE IF NOT EXISTS organizational_structure (
    id UUID DEFAULT (UUID()),
    department VARCHAR(255),
    division VARCHAR(255),
    position VARCHAR(255),
    full_name VARCHAR(255),
    hierarchy_level INTEGER,
    manager_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_department (department),
    INDEX idx_hierarchy (hierarchy_level)
);

-- ====================================
-- Register of deployed agents
-- ====================================
CREATE TABLE IF NOT EXISTS deployed_agents_registry (
    agent_id VARCHAR(255) PRIMARY KEY,
    teams_identity VARCHAR(255),
    channel_roles JSONB,
    status VARCHAR(50) DEFAULT 'active',
    limits JSONB,
    last_activity TIMESTAMP,
    performance_metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id)
);

-- ====================================
-- Operational Memory Table (Task Context))
-- ====================================
CREATE TABLE IF NOT EXISTS operational_memory (
    id UUID DEFAULT (UUID()),
    agent_id VARCHAR(255),
    session_id VARCHAR(255),
    task_context TEXT,
    user_id VARCHAR(255),
    message_history JSONB,
    current_focus TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id),
    INDEX idx_agent_session (agent_id, session_id),
    INDEX idx_user_id (user_id)
);

-- ====================================
-- Core Memory Table (Rules))
-- ====================================
CREATE TABLE IF NOT EXISTS core_memory (
    id UUID DEFAULT (UUID()),
    agent_id VARCHAR(255),
    rule_type VARCHAR(100),
    rule_content TEXT,
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id),
    INDEX idx_agent_rule_type (agent_id, rule_type),
    INDEX idx_priority (priority)
);

-- ====================================
-- Table of chat rooms history
-- ====================================
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID DEFAULT (UUID()),
    agent_id VARCHAR(255),
    user_id VARCHAR(255),
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    session_id VARCHAR(255),
    metadata JSONB DEFAULT ('{}'),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id),
    INDEX idx_agent_user (agent_id, user_id),
    INDEX idx_session (session_id),
    INDEX idx_timestamp (timestamp)
);

-- ====================================
-- System metric table
-- ====================================
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID DEFAULT (UUID()),
    metric_name VARCHAR(255),
    metric_value DECIMAL(10,2),
    agent_id VARCHAR(255),
    period VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (agent_id) REFERENCES agent_configurations(agent_id),
    INDEX idx_metric_name (metric_name),
    INDEX idx_agent_metric (agent_id, metric_name),
    INDEX idx_period (period)
);

-- ====================================
-- Creation of productivity indices
-- ====================================
CREATE INDEX IF NOT EXISTS idx_agent_config_active ON agent_configurations (is_active);
CREATE INDEX IF NOT EXISTS idx_deployed_agents_status ON deployed_agents_registry (status);
CREATE INDEX IF NOT EXISTS idx_chat_history_agent_time ON chat_history (agent_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_operational_memory_agent ON operational_memory (agent_id);

-- ====================================
-- Logging Initialization
-- ====================================
INSERT INTO system_metrics (metric_name, metric_value, agent_id, period) 
VALUES ('database_initialized', 1.0, 'system', 'initialization');

-- ====================================
-- Create user for application
-- ====================================
CREATE USER IF NOT EXISTS 'office_services_user'@'%' IDENTIFIED BY 'office_services_pass';
GRANT ALL PRIVILEGES ON office_services_agents.* TO 'office_services_user'@'%';
FLUSH PRIVILEGES;

-- ====================================
-- Final verification
-- ====================================
SHOW TABLES;
SELECT 'Centralized Agent Database initialized successfully' as status;
