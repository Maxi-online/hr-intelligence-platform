-- ================================================================

-- WORKFLOW OFFICE - CENTRALIZED DATABASE OF AGENCIES

-- Full structure for storage and configuration of AI agents

-- ================================================================

-- Version: 2.1.0

-- Date: 2025-10-13

-- Changes: UUID for agent_id, simplified org structure, added Data/author

-- ================================================================



-- Database development

CREATE DATABASE IF NOT EXISTS office_services_agents 

CHARACTER SET utf8mb4 

COLLATE utf8mb4_unicode_ci;



USE office_services_agents;



-- ================================================================

-- MAIN TABLES OF AGENCIES

-- ================================================================



-- ----------------------------------------------------------------

-- Table: budgets

-- Description: Core list of agents with UUID identifiers

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agents (

    -- Primary Key

    agent_id CHAR(36) PRIMARY KEY COMMENT 'UUID Agent',

    

    -- Basic information

    agent_name VARCHAR(255) NOT NULL COMMENT 'Representative name (e.g.: @boss.ai)',

    agent_type VARCHAR(100) NOT NULL COMMENT 'Type of agent (supervisor, recruiter, scryner, menu, admin))',

    display_name VARCHAR(255) NOT NULL COMMENT 'Human name (e.g.: Alain Sergeyeva)',

    

    -- Role and description

    role VARCHAR(255) NOT NULL COMMENT 'The role of the agent (Supervisor, Active Recruiter, Candidate Scrinner))',

    persona TEXT COMMENT 'Brief description of the identity of the agent',

    description TEXT COMMENT 'Detailed description of the agent and his functions',

    

    -- Identification in platforms

    telegram_username VARCHAR(255) UNIQUE COMMENT 'Telegram username (e.g.: @demo_organization_bossaibot)',

    teams_identity VARCHAR(255) UNIQUE COMMENT 'Microsoft Teams identity',

    slack_identity VARCHAR(255) UNIQUE COMMENT 'Slack identity',

    

    -- Status and version

    version VARCHAR(50) DEFAULT '1.0.0' COMMENT 'Agent configuration version',

    status ENUM('active', 'inactive', 'maintenance', 'archived') DEFAULT 'active' COMMENT 'Current agent status',

    is_active BOOLEAN DEFAULT TRUE COMMENT 'Is the agent active?',

    

    -- Additional metadata

    metadata JSON COMMENT 'Additional Agent Metadata',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date of creation of the record',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Who made the record',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    updated_by VARCHAR(255) DEFAULT 'system' COMMENT 'Who Updated',

    

    -- Indexes

    INDEX idx_agent_type (agent_type),

    INDEX idx_status (status),

    INDEX idx_is_active (is_active),

    INDEX idx_date (date),

    INDEX idx_telegram (telegram_username),

    INDEX idx_teams (teams_identity)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Core table of agents';



-- ----------------------------------------------------------------

-- Table: agent_prompts

-- Description: System prompts of agents with versionivity

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_prompts (

    -- Primary Key

    prompt_id CHAR(36) PRIMARY KEY COMMENT 'UUID Prompta',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    

    -- Prompte

    system_prompt TEXT NOT NULL COMMENT 'Basic system agent prompt',

    tone_of_voice TEXT COMMENT 'The tone and style of communication of the agent',

    

    -- Versionarity

    version VARCHAR(50) NOT NULL COMMENT 'Prompt version',

    is_current BOOLEAN DEFAULT TRUE COMMENT 'Is the current version',

    

    -- Additional instructions

    additional_instructions TEXT COMMENT 'Additional instructions for the agent',

    examples JSON COMMENT 'Examples of dialogues (Few-Shot Learning)',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author of Prompt',

    changelog TEXT COMMENT 'Description of changes to the version',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_version (version),

    INDEX idx_is_current (is_current),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='System prompts of agents';



-- ----------------------------------------------------------------

-- Table: agent_gpt_settings

-- Description: GPT model settings for each agent

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_gpt_settings (

    -- Primary Key

    setting_id CHAR(36) PRIMARY KEY COMMENT 'UUID Settings',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL UNIQUE COMMENT 'UUID Agent (one set of settings per agent)',

    

    -- Model

    model VARCHAR(100) NOT NULL DEFAULT 'gpt-5-nano' COMMENT 'GPT model name (gpt-5-nano, gpt-5, gpt-4.1)',

    

    -- GPT-5 parameters (new)

    reasoning_effort ENUM('minimal', 'low', 'medium', 'high') DEFAULT 'medium' COMMENT 'GPT-5 reasoning level',

    

    -- GPT-4 parameters (old, compatibility)

    temperature DECIMAL(3,2) DEFAULT 0.70 COMMENT 'Temperature (0.0-2.0) - for GPT-4',

    top_p DECIMAL(3,2) DEFAULT 1.00 COMMENT 'Top P (0.0-1.0)',

    frequency_penalty DECIMAL(3,2) DEFAULT 0.00 COMMENT 'Frequency Penalty (0.0-2.0)',

    presence_penalty DECIMAL(3,2) DEFAULT 0.00 COMMENT 'Presence Penalty (0.0-2.0)',

    

    -- Tokens

    max_tokens INTEGER DEFAULT 4096 COMMENT 'Maximum number of currents in response',

    max_context_tokens INTEGER DEFAULT 128000 COMMENT 'Maximum Context (for GPT-5: 1M tokens)',

    

    -- Tool calling

    tool_choice VARCHAR(50) DEFAULT 'auto' COMMENT 'Tool selection strategy (auto, requered, noe)',

    parallel_tool_calls BOOLEAN DEFAULT TRUE COMMENT 'Allow parallel challenges to tools',

    

    -- Optimization

    prompt_cache_enabled BOOLEAN DEFAULT TRUE COMMENT 'Use propt caching',

    prompt_cache_key VARCHAR(255) COMMENT 'Prompt Cash Key',

    stream_enabled BOOLEAN DEFAULT FALSE COMMENT 'Flow transmission of replies',

    

    -- Responses API (GPT-5)

    use_responses_api BOOLEAN DEFAULT TRUE COMMENT 'Use Responsions API for GPT-5',

    response_format JSON COMMENT 'Response format (JSON schema)',

    

    -- Limitations

    max_retries INTEGER DEFAULT 3 COMMENT 'Maximum number of attempts in case of error',

    timeout_seconds INTEGER DEFAULT 60 COMMENT 'Timeout in seconds',

    rate_limit_per_minute INTEGER DEFAULT 60 COMMENT 'Restricts requests per minute',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_model (model),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GPT envelopes for agents';



-- ----------------------------------------------------------------

-- Table: agent_tools

-- Description: Tools (tools) available to agents

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_tools (

    -- Primary Key

    tool_id CHAR(36) PRIMARY KEY COMMENT 'UUID tool',

    

    -- Information on the tool

    tool_name VARCHAR(255) NOT NULL COMMENT 'Name of tool (e.g.: search_resumes)',

    tool_type ENUM('function', 'mcp', 'api', 'database', 'external') DEFAULT 'function' COMMENT 'Type of tool',

    

    -- Description

    description TEXT NOT NULL COMMENT 'Description of GPT tool',

    category VARCHAR(100) COMMENT 'Category of tool (search, analysis, communication)',

    

    -- Parameters

    parameters JSON NOT NULL COMMENT 'JSON tool parameter diagram',

    required_params JSON COMMENT 'Mandatory parameters',

    

    -- Format for MCP

    mcp_server_url VARCHAR(500) COMMENT 'URL MCP servers (e.g.: https://mcp.dadata.ru/mcp)',

    mcp_auth_type ENUM('none', 'bearer', 'api_key', 'oauth') COMMENT 'MCP authentication type',

    mcp_auth_token VARCHAR(500) COMMENT 'Token for MCP',

    

    -- External API configuration

    api_endpoint VARCHAR(500) COMMENT 'Endpoint External API',

    api_method VARCHAR(10) COMMENT 'HTTP Method (GT, POST, PUT)',

    api_headers JSON COMMENT 'Headings for API Request',

    

    -- Status and rights

    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether the tool is active',

    requires_approval BOOLEAN DEFAULT FALSE COMMENT 'Requires user validation',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- Indexes

    INDEX idx_tool_name (tool_name),

    INDEX idx_tool_type (tool_type),

    INDEX idx_is_active (is_active),

    INDEX idx_date (date),

    UNIQUE INDEX idx_tool_name_unique (tool_name)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tools available to agents';



-- ----------------------------------------------------------------

-- Table: agent_tools_mapping

-- Description: Relationship of agents to tools available to them

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_tools_mapping (

    -- Primary Key

    mapping_id CHAR(36) PRIMARY KEY COMMENT 'UUID Communications',

    

    -- Communications

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    tool_id CHAR(36) NOT NULL COMMENT 'UUID tool',

    

    -- Agent tool settings

    is_enabled BOOLEAN DEFAULT TRUE COMMENT 'Do you have an agent tool on?',

    priority INTEGER DEFAULT 0 COMMENT 'Priority of instrument (0 - highest)',

    

    -- Limitations

    rate_limit_per_hour INTEGER COMMENT 'Use limit per hour',

    max_retries INTEGER DEFAULT 3 COMMENT 'Maximum number of attempts',

    

    -- Castle configuration

    custom_params JSON COMMENT 'Castome parameters for this agent',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    FOREIGN KEY (tool_id) REFERENCES agent_tools(tool_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_tool_id (tool_id),

    INDEX idx_is_enabled (is_enabled),

    INDEX idx_date (date),

    UNIQUE INDEX idx_agent_tool_unique (agent_id, tool_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Communication of agents to instruments';



-- ================================================================

-- AGENT MEMORY

-- ================================================================



-- ----------------------------------------------------------------

-- Table: core_memory

-- Core memory agent - critically important rules and facts

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS core_memory (

    -- Primary Key

    memory_id CHAR(36) PRIMARY KEY COMMENT 'UUID memory recording',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    

    -- Type of memory

    memory_type ENUM('rule', 'fact', 'persona', 'constraint', 'knowledge', 'preference') NOT NULL COMMENT 'Type of memory recording',

    memory_category VARCHAR(100) COMMENT 'Category of memory (communication, behavior, domain_knowledge))',

    

    -- Content

    memory_key VARCHAR(255) NOT NULL COMMENT 'Memory key (for example: response_language)',

    memory_value TEXT NOT NULL COMMENT 'The Importance of Memory',

    

    -- Priority

    priority INTEGER DEFAULT 5 COMMENT 'Priority (1 - highest, 10 - low)',

    is_permanent BOOLEAN DEFAULT FALSE COMMENT 'Permanent memory (can not be removed))',

    

    -- Context of application

    applies_to_context JSON COMMENT 'Contexts where applied (e.g.:["conversation", "tool_calling"])',

    

    -- Status

    is_active BOOLEAN DEFAULT TRUE COMMENT 'Is the recording active?',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    tags JSON COMMENT 'Search tags',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_memory_type (memory_type),

    INDEX idx_priority (priority),

    INDEX idx_is_active (is_active),

    INDEX idx_memory_key (memory_key),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Core Memory of Agents';



-- ----------------------------------------------------------------

-- Table: operational_memory

-- Description: Operating memory - the context of current tasks and sessions

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operational_memory (

    -- Primary Key

    operation_id CHAR(36) PRIMARY KEY COMMENT 'UUID Operations',

    

    -- Communications

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    session_id VARCHAR(255) NOT NULL COMMENT 'ID of the user session',

    user_id VARCHAR(255) NOT NULL COMMENT 'User ID',

    

    -- Context of the task

    task_type VARCHAR(100) COMMENT 'Type of task (search, screening, anallysis)',

    task_context TEXT COMMENT 'Context of the current task',

    current_focus TEXT COMMENT 'Current Agent Focus',

    

    -- Data from sessions

    session_data JSON COMMENT 'Data from sessions',

    conversation_summary TEXT COMMENT 'Summary of the conversation',

    

    -- Time data

    temp_data JSON COMMENT 'Time for processing',

    

    -- TTL (Time To Live)

    expires_at TIMESTAMP COMMENT 'Expiry date (auto-dispatch)',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_session (agent_id, session_id),

    INDEX idx_user_id (user_id),

    INDEX idx_expires_at (expires_at),

    INDEX idx_task_type (task_type),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Operational memory of agents';



-- ----------------------------------------------------------------

-- Table: long_term_memory

-- Long-term memory – training and adaptation

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS long_term_memory (

    -- Primary Key

    ltm_id CHAR(36) PRIMARY KEY COMMENT 'UUID Record',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    

    -- Type of record

    memory_type ENUM('learned_pattern', 'user_preference', 'success_case', 'failure_case', 'optimization') NOT NULL COMMENT 'Type of long-term memory',

    

    -- Content

    title VARCHAR(500) NOT NULL COMMENT 'Record Header',

    content TEXT NOT NULL COMMENT 'Content',

    

    -- Context

    context_tags JSON COMMENT 'Legs of context (e.g.:["candidate_screening", "technical_skills"])',

    related_user_id VARCHAR(255) COMMENT 'Linked user (if applicable)',

    

    -- Meterics

    usage_count INTEGER DEFAULT 0 COMMENT 'Number of applications',

    success_rate DECIMAL(5,2) COMMENT 'Percentage success rate',

    last_used_at TIMESTAMP COMMENT 'Latest application',

    

    -- Status

    is_active BOOLEAN DEFAULT TRUE COMMENT 'Is the recording active?',

    confidence_score DECIMAL(5,2) COMMENT 'Confidence level (0.00-100.00)',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_memory_type (memory_type),

    INDEX idx_usage_count (usage_count),

    INDEX idx_last_used (last_used_at),

    INDEX idx_related_user (related_user_id),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Long-term memory of agents';



-- ================================================================

-- BACKGROUND AND LOIGRATION

-- ================================================================



-- ----------------------------------------------------------------

-- Table: chat_history

-- Description: History of all agents &apos; messages

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS chat_history (

    -- Primary Key

    message_id CHAR(36) PRIMARY KEY COMMENT 'UUID Messages',

    

    -- Communications

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    session_id VARCHAR(255) NOT NULL COMMENT 'IDB.2/Dec.29 IDB.2/5',

    user_id VARCHAR(255) NOT NULL COMMENT 'User ID',

    

    -- Communication

    role ENUM('user', 'assistant', 'system', 'tool') NOT NULL COMMENT 'Sender &apos; s Role',

    content TEXT NOT NULL COMMENT 'Content of the message',

    content_type ENUM('text', 'image', 'file', 'tool_call', 'tool_result') DEFAULT 'text' COMMENT 'Type of contents',

    

    -- Tool calling

    tool_calls JSON COMMENT 'Tool calls in the message',

    tool_call_id VARCHAR(255) COMMENT 'ID tool call',

    

    -- Platform

    platform ENUM('telegram', 'teams', 'slack', 'web', 'api') NOT NULL COMMENT 'Communication platform',

    platform_message_id VARCHAR(255) COMMENT 'I.D. messages on the platform',

    

    -- Metadata

    metadata JSON COMMENT 'Additional metadata',

    tokens_used INTEGER COMMENT 'Number of currents used',

    response_time_ms INTEGER COMMENT 'Response time in milliseconds',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) COMMENT 'Author (user_id)',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_user (agent_id, user_id),

    INDEX idx_session (session_id),

    INDEX idx_date (date),

    INDEX idx_platform (platform),

    INDEX idx_agent_date (agent_id, date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='The story of the agents'' chat rooms';



-- ----------------------------------------------------------------

-- Table: agent_activity_log

-- Description: Logic of activity of agents

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_activity_log (

    -- Primary Key

    log_id CHAR(36) PRIMARY KEY COMMENT 'UUID Log Record',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    

    -- Type of activity

    activity_type ENUM('message', 'tool_call', 'error', 'startup', 'shutdown', 'config_change') NOT NULL COMMENT 'Type of activity',

    activity_name VARCHAR(255) COMMENT 'Activity name',

    

    -- Details

    description TEXT COMMENT 'Activity description',

    details JSON COMMENT 'Activity Details',

    

    -- Result

    status ENUM('success', 'failure', 'partial', 'pending') NOT NULL COMMENT 'Status',

    error_message TEXT COMMENT 'Error Message (if there is)',

    

    -- Meterics

    duration_ms INTEGER COMMENT 'Length in milliseconds',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_activity_type (activity_type),

    INDEX idx_date (date),

    INDEX idx_status (status)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Activation log of agents';



-- ----------------------------------------------------------------

-- Table: agent_version_history

-- Description: History of agents configuration versions

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_version_history (

    -- Primary Key

    history_id CHAR(36) PRIMARY KEY COMMENT 'UUID History Record',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    

    -- Version

    version VARCHAR(50) NOT NULL COMMENT 'The configuration version',

    previous_version VARCHAR(50) COMMENT 'Previous version',

    

    -- Changes

    change_type ENUM('prompt', 'settings', 'tools', 'memory', 'full_config') NOT NULL COMMENT 'Type of change',

    changelog TEXT NOT NULL COMMENT 'Description of changes',

    

    -- Data before and after

    config_snapshot_before JSON COMMENT 'Snapshot configuration before change',

    config_snapshot_after JSON COMMENT 'Snapshot configuration after change',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date of amendment',

    author VARCHAR(255) NOT NULL COMMENT 'Who made the change?',

    change_reason TEXT COMMENT 'Reason for change',

    is_rollback BOOLEAN DEFAULT FALSE COMMENT '♪ Is it a rebound ♪',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_version (version),

    INDEX idx_change_type (change_type),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='History of agents'' versions';



-- ================================================================

-- RULES AND CONFIGURES

-- ================================================================



-- ----------------------------------------------------------------

-- Table: agent_rules

-- Description: Rules of conduct for agents

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_rules (

    -- Primary Key

    rule_id CHAR(36) PRIMARY KEY COMMENT 'UUID Rules',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    

    -- Rule

    rule_type ENUM('communication', 'behavior', 'security', 'delegation', 'escalation') NOT NULL COMMENT 'Type of rule',

    rule_name VARCHAR(255) NOT NULL COMMENT 'Title of the rule',

    rule_content TEXT NOT NULL COMMENT 'Content of the rule',

    

    -- Conditions of application

    applies_when JSON COMMENT 'Conditions for the application of the rule',

    priority INTEGER DEFAULT 5 COMMENT 'Priority of the rule (1 - highest)',

    

    -- Status

    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether the rule is active',

    is_overridable BOOLEAN DEFAULT TRUE COMMENT 'Can You Resize',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author of the rule',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_rule_type (rule_type),

    INDEX idx_priority (priority),

    INDEX idx_is_active (is_active),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Rules of conduct for agents';



-- ----------------------------------------------------------------

-- Table: agent_routing_rules

-- Description: Inter-agent router rules

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_routing_rules (

    -- Primary Key

    routing_id CHAR(36) PRIMARY KEY COMMENT 'UUID router rules',

    

    -- Communications

    source_agent_id CHAR(36) NOT NULL COMMENT 'UUID Source Agent',

    target_agent_id CHAR(36) NOT NULL COMMENT 'UUID Receiving Agent',

    

    -- Rule

    routing_type ENUM('delegation', 'escalation', 'collaboration', 'report') NOT NULL COMMENT 'Type of routeting',

    routing_condition TEXT COMMENT 'Condition of routement',

    

    -- Settings

    is_bidirectional BOOLEAN DEFAULT FALSE COMMENT 'Two-pronged rule',

    requires_approval BOOLEAN DEFAULT FALSE COMMENT 'Needs confirmation',

    priority INTEGER DEFAULT 5 COMMENT 'Priority of routeting',

    

    -- Status

    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether the rule is active',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (source_agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    FOREIGN KEY (target_agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_source_agent (source_agent_id),

    INDEX idx_target_agent (target_agent_id),

    INDEX idx_routing_type (routing_type),

    INDEX idx_is_active (is_active),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Inter-agent route rules';



-- ================================================================

-- DATA AND KNOWLEDGE

-- ================================================================



-- ----------------------------------------------------------------

-- Table: agent_training_data

-- Description: Training data for agents

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_training_data (

    -- Primary Key

    training_id CHAR(36) PRIMARY KEY COMMENT 'UUID training data',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    

    -- Data type

    data_type ENUM('example', 'knowledge_base', 'faq', 'scenario', 'case_study') NOT NULL COMMENT 'Type of training data',

    category VARCHAR(100) COMMENT 'Data category',

    

    -- Data

    title VARCHAR(500) NOT NULL COMMENT 'Heading',

    content TEXT NOT NULL COMMENT 'Content',

    

    -- Structured data for Few-Shot

    input_example TEXT COMMENT 'Example of input data',

    output_example TEXT COMMENT 'Example of output data',

    

    -- Context

    tags JSON COMMENT 'Search tags',

    context JSON COMMENT 'Context of application',

    

    -- Priority

    priority INTEGER DEFAULT 5 COMMENT 'Priority of use',

    

    -- Status

    is_active BOOLEAN DEFAULT TRUE COMMENT 'Data active',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Data Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_data_type (data_type),

    INDEX idx_category (category),

    INDEX idx_is_active (is_active),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Training agents';



-- ----------------------------------------------------------------

-- Table: agent_knowledge_base

-- Description: Knowledge base of agents (RAG)

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_knowledge_base (

    -- Primary Key

    knowledge_id CHAR(36) PRIMARY KEY COMMENT 'UUID Knowledge Recording',

    

    -- Communication with the agent

    agent_id CHAR(36) COMMENT 'UUID Agent (NULL for general knowledge)',

    

    -- Knowledge

    title VARCHAR(500) NOT NULL COMMENT 'Heading',

    content TEXT NOT NULL COMMENT 'Knowledge content',

    source VARCHAR(500) COMMENT 'Source of knowledge',

    

    -- Categorization

    category VARCHAR(100) NOT NULL COMMENT 'Knowledge category',

    subcategory VARCHAR(100) COMMENT 'Subcategory',

    tags JSON COMMENT 'Search tags',

    

    -- Vectorization (for semantic survey)

    embedding_vector JSON COMMENT 'Vector representation (for RAG)',

    embedding_model VARCHAR(100) COMMENT 'Model for Embedding',

    

    -- Meterics of use

    access_count INTEGER DEFAULT 0 COMMENT 'Number of requests',

    last_accessed_at TIMESTAMP COMMENT 'Last call',

    relevance_score DECIMAL(5,2) COMMENT 'Assessment of relevance',

    

    -- Status

    is_active BOOLEAN DEFAULT TRUE COMMENT 'Whether knowledge is active',

    is_verified BOOLEAN DEFAULT FALSE COMMENT 'Knowledge checked',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_category (category),

    INDEX idx_access_count (access_count),

    INDEX idx_last_accessed (last_accessed_at),

    INDEX idx_date (date),

    FULLTEXT INDEX idx_content_search (title, content)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Knowledge base of agents';



-- ================================================================

-- ORGANIZATIONAL STRUCTURE AND DEPLOYMENT

-- ================================================================



-- ----------------------------------------------------------------

-- Table: organizational_structure

-- Description: Simplified organizational structure of the company

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS organizational_structure (

    -- Primary Key

    id CHAR(36) PRIMARY KEY COMMENT 'UUID Record',

    

    -- Structure

    department VARCHAR(255) NOT NULL COMMENT 'Division (HR, IT, Finance, Sales)',

    position VARCHAR(255) NOT NULL COMMENT 'Post',

    

    -- Staff member

    full_name VARCHAR(255) NOT NULL COMMENT 'Staff member &apos; s IRS',

    

    -- Hierarchy

    hierarchy_level INTEGER NOT NULL COMMENT 'Level of hierarchy (1 - top management)',

    

    -- Communication with the agent

    agent_id CHAR(36) COMMENT 'UUID agent (if it''s an AI employee)',

    

    -- Status

    is_active BOOLEAN DEFAULT TRUE COMMENT 'Staff member active',

    employment_type ENUM('full_time', 'part_time', 'contract', 'ai_agent') DEFAULT 'full_time' COMMENT 'Type of employment',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date established',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE SET NULL,

    

    -- Indexes

    INDEX idx_department (department),

    INDEX idx_hierarchy (hierarchy_level),

    INDEX idx_agent_id (agent_id),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Organizational structure';



-- ----------------------------------------------------------------

-- Table: deployed_agents_registry

-- Description: Register of deployed agents

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS deployed_agents_registry (

    -- Primary Key

    deployment_id CHAR(36) PRIMARY KEY COMMENT 'UUID deployment',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    

    -- Identification on platforms

    telegram_bot_token VARCHAR(500) COMMENT 'Telegram Bot Token',

    telegram_username VARCHAR(255) COMMENT 'Telegram username',

    teams_app_id VARCHAR(255) COMMENT 'Microsoft Teams App ID',

    teams_bot_id VARCHAR(255) COMMENT 'Microsoft Teams Bot ID',

    slack_app_id VARCHAR(255) COMMENT 'Slack App ID',

    slack_bot_token VARCHAR(500) COMMENT 'Slack Bot Token',

    

    -- Roles in canals

    channel_roles JSON COMMENT 'Channel Roles (JSON)',

    

    -- Deployment status

    deployment_status ENUM('deployed', 'stopped', 'maintenance', 'error') DEFAULT 'deployed' COMMENT 'Deployment status',

    last_health_check TIMESTAMP COMMENT 'Last health check',

    

    -- LIMITS AND RESTRICTIONS

    limits JSON COMMENT 'Limites (rat limits, quotas)',

    

    -- Productivity metrics

    performance_metrics JSON COMMENT 'Productivity metrics',

    last_activity TIMESTAMP COMMENT 'Last Activity',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date of deployment',

    author VARCHAR(255) DEFAULT 'system' COMMENT '♪ Who turned ♪',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update date',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_id (agent_id),

    INDEX idx_deployment_status (deployment_status),

    INDEX idx_last_activity (last_activity),

    INDEX idx_date (date),

    UNIQUE INDEX idx_telegram_username (telegram_username)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Register of deployed agents';



-- ================================================================

-- METRICS AND ANALYSIS

-- ================================================================



-- ----------------------------------------------------------------

-- Table: agent_performance_metrics

-- Description: Metrics of agent productivity

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_performance_metrics (

    -- Primary Key

    metric_id CHAR(36) PRIMARY KEY COMMENT 'UUID metrics',

    

    -- Communication with the agent

    agent_id CHAR(36) NOT NULL COMMENT 'UUID Agent',

    

    -- Type of metric

    metric_name VARCHAR(255) NOT NULL COMMENT 'The name of the metrics',

    metric_type ENUM('counter', 'gauge', 'histogram', 'rate') NOT NULL COMMENT 'Type of metric',

    

    -- Value

    metric_value DECIMAL(20,6) NOT NULL COMMENT 'Meaning of metrics',

    metric_unit VARCHAR(50) COMMENT 'Unit',

    

    -- Temporary period

    period ENUM('minute', 'hour', 'day', 'week', 'month') NOT NULL COMMENT 'Period of metrics',

    period_start TIMESTAMP NOT NULL COMMENT 'Opening of period',

    period_end TIMESTAMP NOT NULL COMMENT 'End of period',

    

    -- Additional data

    dimensions JSON COMMENT 'Additional measurements (tags)',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date of entry',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_agent_metric (agent_id, metric_name),

    INDEX idx_period (period),

    INDEX idx_period_start (period_start),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Actors productivity metrics';



-- ----------------------------------------------------------------

-- Table: system_metrics

-- Description: System metrics

-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS system_metrics (

    -- Primary Key

    id CHAR(36) PRIMARY KEY COMMENT 'UUID metrics',

    

    -- Meteric

    metric_name VARCHAR(255) NOT NULL COMMENT 'The name of the metrics',

    metric_value DECIMAL(20,6) NOT NULL COMMENT 'Value',

    

    -- Liaison with the agent (optimal)

    agent_id CHAR(36) COMMENT 'UUID Agent (if applicable)',

    

    -- Period

    period VARCHAR(50) COMMENT 'Period (today, week, month, initialization)',

    

    -- Metadata

    metadata JSON COMMENT 'Additional data',

    

    -- Audit

    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Date of entry',

    author VARCHAR(255) DEFAULT 'system' COMMENT 'Author',

    

    -- External keys

    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,

    

    -- Indexes

    INDEX idx_metric_name (metric_name),

    INDEX idx_agent_metric (agent_id, metric_name),

    INDEX idx_period (period),

    INDEX idx_date (date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='System metrics';



-- ================================================================

-- SUBMISSIONS (VIEWS)

-- ================================================================



-- ----------------------------------------------------------------

-- Presentation: active_agents_view

-- Description: List of active agents with basic information

-- ----------------------------------------------------------------

CREATE OR REPLACE VIEW active_agents_view AS

SELECT 

    a.agent_id,

    a.agent_name,

    a.display_name,

    a.role,

    a.agent_type,

    a.telegram_username,

    a.teams_identity,

    a.status,

    ags.model,

    ags.reasoning_effort,

    COUNT(DISTINCT atm.tool_id) as tools_count,

    COUNT(DISTINCT cm.memory_id) as core_memory_count,

    d.deployment_status,

    d.last_activity,

    a.date as created_at,

    a.updated_at

FROM agents a

LEFT JOIN agent_gpt_settings ags ON a.agent_id = ags.agent_id

LEFT JOIN agent_tools_mapping atm ON a.agent_id = atm.agent_id AND atm.is_enabled = TRUE

LEFT JOIN core_memory cm ON a.agent_id = cm.agent_id AND cm.is_active = TRUE

LEFT JOIN deployed_agents_registry d ON a.agent_id = d.agent_id

WHERE a.is_active = TRUE

GROUP BY a.agent_id;



-- ----------------------------------------------------------------

-- Presentation: agent_full_config_view

-- Description: Full agent configuration

-- ----------------------------------------------------------------

CREATE OR REPLACE VIEW agent_full_config_view AS

SELECT 

    a.agent_id,

    a.agent_name,

    a.display_name,

    a.role,

    a.persona,

    ap.system_prompt,

    ap.tone_of_voice,

    ap.version as prompt_version,

    ags.model,

    ags.reasoning_effort,

    ags.max_tokens,

    ags.tool_choice,

    ags.parallel_tool_calls,

    GROUP_CONCAT(DISTINCT at.tool_name) as available_tools,

    a.status,

    a.date as created_at,

    a.updated_at

FROM agents a

LEFT JOIN agent_prompts ap ON a.agent_id = ap.agent_id AND ap.is_current = TRUE

LEFT JOIN agent_gpt_settings ags ON a.agent_id = ags.agent_id

LEFT JOIN agent_tools_mapping atm ON a.agent_id = atm.agent_id AND atm.is_enabled = TRUE

LEFT JOIN agent_tools at ON atm.tool_id = at.tool_id

GROUP BY a.agent_id;



-- ================================================================

-- TRIGGERS

-- ================================================================



-- ----------------------------------------------------------------

-- Trigger: after_agent_update

-- Description: Automatic writing in the history of versions

-- ----------------------------------------------------------------

DELIMITER $$

CREATE TRIGGER after_agent_update

AFTER UPDATE ON agents

FOR EACH ROW

BEGIN

    IF OLD.version != NEW.version THEN

        INSERT INTO agent_version_history (

            history_id,

            agent_id,

            version,

            previous_version,

            change_type,

            changelog,

            author,

            date

        ) VALUES (

            UUID(),

            NEW.agent_id,

            NEW.version,

            OLD.version,

            'full_config',

            CONCAT('Agent updated from version ', OLD.version, ' to ', NEW.version),

            NEW.updated_by,

            CURRENT_TIMESTAMP

        );

    END IF;

END$$

DELIMITER ;



-- ----------------------------------------------------------------

-- Event: cleanup_expired_operational_memory

-- Description: Automatic cleaning of exhausted operating memory

-- ----------------------------------------------------------------

DELIMITER $$

CREATE EVENT IF NOT EXISTS cleanup_expired_operational_memory

ON SCHEDULE EVERY 1 HOUR

DO

BEGIN

    DELETE FROM operational_memory

    WHERE expires_at IS NOT NULL AND expires_at < NOW();

END$$

DELIMITER ;



-- ================================================================

-- FIRST DATA

-- ================================================================



-- Introduction of Systemic Initialization Metrics

INSERT INTO system_metrics (id, metric_name, metric_value, agent_id, period, date, author) 

VALUES (

    UUID(),

    'database_schema_version',

    2.1,

    NULL,

    'initialization',

    CURRENT_TIMESTAMP,

    'system'

);



-- ================================================================

-- Conclusion

-- ================================================================



SELECT 'Workflow Office - Centralized Agent Database Schema v2.1 initialized successfully!' as status;

SELECT COUNT(*) as total_tables FROM information_schema.tables WHERE table_schema = 'office_services_agents';

