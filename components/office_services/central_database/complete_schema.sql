-- ================================================================
-- WORKFLOW OFFICE - ЦЕНТРАЛИЗОВАННАЯ БАЗА ДАННЫХ АГЕНТОВ
-- Полная структура для хранения AI-агентов и их конфигураций
-- ================================================================
-- Версия: 2.1.0
-- Дата: 2025-10-13
-- Изменения: UUID для agent_id, упрощена org структура, добавлены date/author
-- ================================================================

-- Создание базы данных
CREATE DATABASE IF NOT EXISTS office_services_agents 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE office_services_agents;

-- ================================================================
-- ОСНОВНЫЕ ТАБЛИЦЫ АГЕНТОВ
-- ================================================================

-- ----------------------------------------------------------------
-- Таблица: agents
-- Описание: Основная таблица агентов с UUID идентификаторами
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agents (
    -- Первичный ключ
    agent_id CHAR(36) PRIMARY KEY COMMENT 'UUID агента',
    
    -- Базовая информация
    agent_name VARCHAR(255) NOT NULL COMMENT 'Отображаемое имя агента (например: @boss.ai)',
    agent_type VARCHAR(100) NOT NULL COMMENT 'Тип агента (supervisor, recruiter, scrinner, menu, admin)',
    display_name VARCHAR(255) NOT NULL COMMENT 'Человеческое имя (например: Алена Сергеева)',
    
    -- Роль и описание
    role VARCHAR(255) NOT NULL COMMENT 'Роль агента (Supervisor, Active Recruiter, Candidate Scrinner)',
    persona TEXT COMMENT 'Краткое описание личности агента',
    description TEXT COMMENT 'Детальное описание агента и его функций',
    
    -- Идентификация в платформах
    telegram_username VARCHAR(255) UNIQUE COMMENT 'Telegram username (например: @demo_organization_bossaibot)',
    teams_identity VARCHAR(255) UNIQUE COMMENT 'Microsoft Teams identity',
    slack_identity VARCHAR(255) UNIQUE COMMENT 'Slack identity',
    
    -- Статус и версия
    version VARCHAR(50) DEFAULT '1.0.0' COMMENT 'Версия конфигурации агента',
    status ENUM('active', 'inactive', 'maintenance', 'archived') DEFAULT 'active' COMMENT 'Текущий статус агента',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активен ли агент',
    
    -- Дополнительные метаданные
    metadata JSON COMMENT 'Дополнительные метаданные агента',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания записи',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Кто создал запись',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    updated_by VARCHAR(255) DEFAULT 'system' COMMENT 'Кто обновил',
    
    -- Индексы
    INDEX idx_agent_type (agent_type),
    INDEX idx_status (status),
    INDEX idx_is_active (is_active),
    INDEX idx_date (date),
    INDEX idx_telegram (telegram_username),
    INDEX idx_teams (teams_identity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Основная таблица агентов';

-- ----------------------------------------------------------------
-- Таблица: agent_prompts
-- Описание: Системные промпты агентов с версионностью
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_prompts (
    -- Первичный ключ
    prompt_id CHAR(36) PRIMARY KEY COMMENT 'UUID промпта',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    
    -- Промпт
    system_prompt TEXT NOT NULL COMMENT 'Основной системный промпт агента',
    tone_of_voice TEXT COMMENT 'Тон и стиль общения агента',
    
    -- Версионность
    version VARCHAR(50) NOT NULL COMMENT 'Версия промпта',
    is_current BOOLEAN DEFAULT TRUE COMMENT 'Является ли текущей версией',
    
    -- Дополнительные инструкции
    additional_instructions TEXT COMMENT 'Дополнительные инструкции для агента',
    examples JSON COMMENT 'Примеры диалогов (Few-Shot Learning)',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор промпта',
    changelog TEXT COMMENT 'Описание изменений в версии',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_version (version),
    INDEX idx_is_current (is_current),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Системные промпты агентов';

-- ----------------------------------------------------------------
-- Таблица: agent_gpt_settings
-- Описание: Настройки GPT модели для каждого агента
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_gpt_settings (
    -- Первичный ключ
    setting_id CHAR(36) PRIMARY KEY COMMENT 'UUID настройки',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL UNIQUE COMMENT 'UUID агента (один набор настроек на агента)',
    
    -- Модель
    model VARCHAR(100) NOT NULL DEFAULT 'gpt-5-nano' COMMENT 'Название модели GPT (gpt-5-nano, gpt-5, gpt-4.1)',
    
    -- Параметры GPT-5 (новые)
    reasoning_effort ENUM('minimal', 'low', 'medium', 'high') DEFAULT 'medium' COMMENT 'Уровень рассуждений GPT-5 (заменяет temperature)',
    
    -- Параметры GPT-4 (старые, для совместимости)
    temperature DECIMAL(3,2) DEFAULT 0.70 COMMENT 'Temperature (0.0-2.0) - для GPT-4',
    top_p DECIMAL(3,2) DEFAULT 1.00 COMMENT 'Top P (0.0-1.0)',
    frequency_penalty DECIMAL(3,2) DEFAULT 0.00 COMMENT 'Frequency Penalty (0.0-2.0)',
    presence_penalty DECIMAL(3,2) DEFAULT 0.00 COMMENT 'Presence Penalty (0.0-2.0)',
    
    -- Токены
    max_tokens INTEGER DEFAULT 4096 COMMENT 'Максимальное количество токенов в ответе',
    max_context_tokens INTEGER DEFAULT 128000 COMMENT 'Максимальный контекст (для GPT-5: 1M tokens)',
    
    -- Tool calling
    tool_choice VARCHAR(50) DEFAULT 'auto' COMMENT 'Стратегия выбора инструментов (auto, required, none)',
    parallel_tool_calls BOOLEAN DEFAULT TRUE COMMENT 'Разрешить параллельные вызовы инструментов',
    
    -- Оптимизация
    prompt_cache_enabled BOOLEAN DEFAULT TRUE COMMENT 'Использовать prompt caching',
    prompt_cache_key VARCHAR(255) COMMENT 'Ключ для кеширования промпта',
    stream_enabled BOOLEAN DEFAULT FALSE COMMENT 'Потоковая передача ответов',
    
    -- Responses API (GPT-5)
    use_responses_api BOOLEAN DEFAULT TRUE COMMENT 'Использовать Responses API для GPT-5',
    response_format JSON COMMENT 'Формат ответа (JSON schema)',
    
    -- Ограничения
    max_retries INTEGER DEFAULT 3 COMMENT 'Максимальное количество попыток при ошибке',
    timeout_seconds INTEGER DEFAULT 60 COMMENT 'Таймаут запроса в секундах',
    rate_limit_per_minute INTEGER DEFAULT 60 COMMENT 'Лимит запросов в минуту',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_model (model),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Настройки GPT для агентов';

-- ----------------------------------------------------------------
-- Таблица: agent_tools
-- Описание: Инструменты (tools) доступные агентам
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_tools (
    -- Первичный ключ
    tool_id CHAR(36) PRIMARY KEY COMMENT 'UUID инструмента',
    
    -- Информация об инструменте
    tool_name VARCHAR(255) NOT NULL COMMENT 'Название инструмента (например: search_resumes)',
    tool_type ENUM('function', 'mcp', 'api', 'database', 'external') DEFAULT 'function' COMMENT 'Тип инструмента',
    
    -- Описание
    description TEXT NOT NULL COMMENT 'Описание инструмента для GPT',
    category VARCHAR(100) COMMENT 'Категория инструмента (search, analysis, communication)',
    
    -- Параметры
    parameters JSON NOT NULL COMMENT 'JSON схема параметров инструмента',
    required_params JSON COMMENT 'Обязательные параметры',
    
    -- Конфигурация для MCP
    mcp_server_url VARCHAR(500) COMMENT 'URL MCP сервера (например: https://mcp.dadata.ru/mcp)',
    mcp_auth_type ENUM('none', 'bearer', 'api_key', 'oauth') COMMENT 'Тип аутентификации MCP',
    mcp_auth_token VARCHAR(500) COMMENT 'Токен для MCP',
    
    -- Конфигурация для внешних API
    api_endpoint VARCHAR(500) COMMENT 'Endpoint внешнего API',
    api_method VARCHAR(10) COMMENT 'HTTP метод (GET, POST, PUT)',
    api_headers JSON COMMENT 'Заголовки для API запроса',
    
    -- Статус и права
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активен ли инструмент',
    requires_approval BOOLEAN DEFAULT FALSE COMMENT 'Требует подтверждения пользователя',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Индексы
    INDEX idx_tool_name (tool_name),
    INDEX idx_tool_type (tool_type),
    INDEX idx_is_active (is_active),
    INDEX idx_date (date),
    UNIQUE INDEX idx_tool_name_unique (tool_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Инструменты доступные агентам';

-- ----------------------------------------------------------------
-- Таблица: agent_tools_mapping
-- Описание: Связь агентов с доступными им инструментами
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_tools_mapping (
    -- Первичный ключ
    mapping_id CHAR(36) PRIMARY KEY COMMENT 'UUID связи',
    
    -- Связи
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    tool_id CHAR(36) NOT NULL COMMENT 'UUID инструмента',
    
    -- Настройки инструмента для агента
    is_enabled BOOLEAN DEFAULT TRUE COMMENT 'Включен ли инструмент для агента',
    priority INTEGER DEFAULT 0 COMMENT 'Приоритет инструмента (0 - наивысший)',
    
    -- Ограничения
    rate_limit_per_hour INTEGER COMMENT 'Лимит использований в час',
    max_retries INTEGER DEFAULT 3 COMMENT 'Максимальное количество попыток',
    
    -- Кастомная конфигурация
    custom_params JSON COMMENT 'Кастомные параметры для этого агента',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (tool_id) REFERENCES agent_tools(tool_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_tool_id (tool_id),
    INDEX idx_is_enabled (is_enabled),
    INDEX idx_date (date),
    UNIQUE INDEX idx_agent_tool_unique (agent_id, tool_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Связь агентов с инструментами';

-- ================================================================
-- ПАМЯТЬ АГЕНТОВ
-- ================================================================

-- ----------------------------------------------------------------
-- Таблица: core_memory
-- Описание: Core память агента - критически важные правила и факты
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core_memory (
    -- Первичный ключ
    memory_id CHAR(36) PRIMARY KEY COMMENT 'UUID записи памяти',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    
    -- Тип памяти
    memory_type ENUM('rule', 'fact', 'persona', 'constraint', 'knowledge', 'preference') NOT NULL COMMENT 'Тип записи памяти',
    memory_category VARCHAR(100) COMMENT 'Категория памяти (communication, behavior, domain_knowledge)',
    
    -- Содержимое
    memory_key VARCHAR(255) NOT NULL COMMENT 'Ключ памяти (например: response_language)',
    memory_value TEXT NOT NULL COMMENT 'Значение памяти',
    
    -- Приоритет
    priority INTEGER DEFAULT 5 COMMENT 'Приоритет (1 - наивысший, 10 - низкий)',
    is_permanent BOOLEAN DEFAULT FALSE COMMENT 'Постоянная память (нельзя удалить)',
    
    -- Контекст применения
    applies_to_context JSON COMMENT 'Контексты, где применяется (например: ["conversation", "tool_calling"])',
    
    -- Статус
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активна ли запись',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    tags JSON COMMENT 'Теги для поиска',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_memory_type (memory_type),
    INDEX idx_priority (priority),
    INDEX idx_is_active (is_active),
    INDEX idx_memory_key (memory_key),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Core память агентов';

-- ----------------------------------------------------------------
-- Таблица: operational_memory
-- Описание: Оперативная память - контекст текущих задач и сессий
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS operational_memory (
    -- Первичный ключ
    operation_id CHAR(36) PRIMARY KEY COMMENT 'UUID операции',
    
    -- Связи
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    session_id VARCHAR(255) NOT NULL COMMENT 'ID сессии пользователя',
    user_id VARCHAR(255) NOT NULL COMMENT 'ID пользователя',
    
    -- Контекст задачи
    task_type VARCHAR(100) COMMENT 'Тип задачи (search, screening, analysis)',
    task_context TEXT COMMENT 'Контекст текущей задачи',
    current_focus TEXT COMMENT 'Текущий фокус внимания агента',
    
    -- Данные сессии
    session_data JSON COMMENT 'Данные сессии',
    conversation_summary TEXT COMMENT 'Краткое содержание разговора',
    
    -- Временные данные
    temp_data JSON COMMENT 'Временные данные для обработки',
    
    -- TTL (Time To Live)
    expires_at TIMESTAMP COMMENT 'Дата истечения (автоудаление)',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_session (agent_id, session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at),
    INDEX idx_task_type (task_type),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Оперативная память агентов';

-- ----------------------------------------------------------------
-- Таблица: long_term_memory
-- Описание: Долговременная память - обучение и адаптация
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS long_term_memory (
    -- Первичный ключ
    ltm_id CHAR(36) PRIMARY KEY COMMENT 'UUID записи',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    
    -- Тип записи
    memory_type ENUM('learned_pattern', 'user_preference', 'success_case', 'failure_case', 'optimization') NOT NULL COMMENT 'Тип долговременной памяти',
    
    -- Содержимое
    title VARCHAR(500) NOT NULL COMMENT 'Заголовок записи',
    content TEXT NOT NULL COMMENT 'Содержимое',
    
    -- Контекст
    context_tags JSON COMMENT 'Теги контекста (например: ["candidate_screening", "technical_skills"])',
    related_user_id VARCHAR(255) COMMENT 'Связанный пользователь (если применимо)',
    
    -- Метрики
    usage_count INTEGER DEFAULT 0 COMMENT 'Количество применений',
    success_rate DECIMAL(5,2) COMMENT 'Процент успеха применения',
    last_used_at TIMESTAMP COMMENT 'Последнее применение',
    
    -- Статус
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активна ли запись',
    confidence_score DECIMAL(5,2) COMMENT 'Уровень уверенности (0.00-100.00)',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_memory_type (memory_type),
    INDEX idx_usage_count (usage_count),
    INDEX idx_last_used (last_used_at),
    INDEX idx_related_user (related_user_id),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Долговременная память агентов';

-- ================================================================
-- ИСТОРИЯ И ЛОГИРОВАНИЕ
-- ================================================================

-- ----------------------------------------------------------------
-- Таблица: chat_history
-- Описание: История всех сообщений агентов
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_history (
    -- Первичный ключ
    message_id CHAR(36) PRIMARY KEY COMMENT 'UUID сообщения',
    
    -- Связи
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    session_id VARCHAR(255) NOT NULL COMMENT 'ID сессии',
    user_id VARCHAR(255) NOT NULL COMMENT 'ID пользователя',
    
    -- Сообщение
    role ENUM('user', 'assistant', 'system', 'tool') NOT NULL COMMENT 'Роль отправителя',
    content TEXT NOT NULL COMMENT 'Содержимое сообщения',
    content_type ENUM('text', 'image', 'file', 'tool_call', 'tool_result') DEFAULT 'text' COMMENT 'Тип содержимого',
    
    -- Tool calling
    tool_calls JSON COMMENT 'Вызовы инструментов в сообщении',
    tool_call_id VARCHAR(255) COMMENT 'ID вызова инструмента',
    
    -- Платформа
    platform ENUM('telegram', 'teams', 'slack', 'web', 'api') NOT NULL COMMENT 'Платформа сообщения',
    platform_message_id VARCHAR(255) COMMENT 'ID сообщения на платформе',
    
    -- Метаданные
    metadata JSON COMMENT 'Дополнительные метаданные',
    tokens_used INTEGER COMMENT 'Количество использованных токенов',
    response_time_ms INTEGER COMMENT 'Время ответа в миллисекундах',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) COMMENT 'Автор (user_id)',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_user (agent_id, user_id),
    INDEX idx_session (session_id),
    INDEX idx_date (date),
    INDEX idx_platform (platform),
    INDEX idx_agent_date (agent_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='История чатов агентов';

-- ----------------------------------------------------------------
-- Таблица: agent_activity_log
-- Описание: Лог активности агентов
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_activity_log (
    -- Первичный ключ
    log_id CHAR(36) PRIMARY KEY COMMENT 'UUID записи лога',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    
    -- Тип активности
    activity_type ENUM('message', 'tool_call', 'error', 'startup', 'shutdown', 'config_change') NOT NULL COMMENT 'Тип активности',
    activity_name VARCHAR(255) COMMENT 'Название активности',
    
    -- Детали
    description TEXT COMMENT 'Описание активности',
    details JSON COMMENT 'Детали активности',
    
    -- Результат
    status ENUM('success', 'failure', 'partial', 'pending') NOT NULL COMMENT 'Статус выполнения',
    error_message TEXT COMMENT 'Сообщение об ошибке (если есть)',
    
    -- Метрики
    duration_ms INTEGER COMMENT 'Длительность в миллисекундах',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_activity_type (activity_type),
    INDEX idx_date (date),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Лог активности агентов';

-- ----------------------------------------------------------------
-- Таблица: agent_version_history
-- Описание: История версий конфигураций агентов
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_version_history (
    -- Первичный ключ
    history_id CHAR(36) PRIMARY KEY COMMENT 'UUID записи истории',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    
    -- Версия
    version VARCHAR(50) NOT NULL COMMENT 'Версия конфигурации',
    previous_version VARCHAR(50) COMMENT 'Предыдущая версия',
    
    -- Изменения
    change_type ENUM('prompt', 'settings', 'tools', 'memory', 'full_config') NOT NULL COMMENT 'Тип изменения',
    changelog TEXT NOT NULL COMMENT 'Описание изменений',
    
    -- Данные до и после
    config_snapshot_before JSON COMMENT 'Снапшот конфигурации до изменения',
    config_snapshot_after JSON COMMENT 'Снапшот конфигурации после изменения',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата изменения',
    author VARCHAR(255) NOT NULL COMMENT 'Кто внес изменения',
    change_reason TEXT COMMENT 'Причина изменения',
    is_rollback BOOLEAN DEFAULT FALSE COMMENT 'Является ли откатом',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_version (version),
    INDEX idx_change_type (change_type),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='История версий агентов';

-- ================================================================
-- ПРАВИЛА И КОНФИГУРАЦИИ
-- ================================================================

-- ----------------------------------------------------------------
-- Таблица: agent_rules
-- Описание: Правила поведения агентов
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_rules (
    -- Первичный ключ
    rule_id CHAR(36) PRIMARY KEY COMMENT 'UUID правила',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    
    -- Правило
    rule_type ENUM('communication', 'behavior', 'security', 'delegation', 'escalation') NOT NULL COMMENT 'Тип правила',
    rule_name VARCHAR(255) NOT NULL COMMENT 'Название правила',
    rule_content TEXT NOT NULL COMMENT 'Содержимое правила',
    
    -- Условия применения
    applies_when JSON COMMENT 'Условия применения правила',
    priority INTEGER DEFAULT 5 COMMENT 'Приоритет правила (1 - наивысший)',
    
    -- Статус
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активно ли правило',
    is_overridable BOOLEAN DEFAULT TRUE COMMENT 'Можно ли переопределить',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор правила',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_rule_type (rule_type),
    INDEX idx_priority (priority),
    INDEX idx_is_active (is_active),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Правила поведения агентов';

-- ----------------------------------------------------------------
-- Таблица: agent_routing_rules
-- Описание: Правила маршрутизации между агентами
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_routing_rules (
    -- Первичный ключ
    routing_id CHAR(36) PRIMARY KEY COMMENT 'UUID правила маршрутизации',
    
    -- Связи
    source_agent_id CHAR(36) NOT NULL COMMENT 'UUID агента-источника',
    target_agent_id CHAR(36) NOT NULL COMMENT 'UUID агента-получателя',
    
    -- Правило
    routing_type ENUM('delegation', 'escalation', 'collaboration', 'report') NOT NULL COMMENT 'Тип маршрутизации',
    routing_condition TEXT COMMENT 'Условие маршрутизации',
    
    -- Настройки
    is_bidirectional BOOLEAN DEFAULT FALSE COMMENT 'Двунаправленное правило',
    requires_approval BOOLEAN DEFAULT FALSE COMMENT 'Требует подтверждения',
    priority INTEGER DEFAULT 5 COMMENT 'Приоритет маршрутизации',
    
    -- Статус
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активно ли правило',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (source_agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (target_agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_source_agent (source_agent_id),
    INDEX idx_target_agent (target_agent_id),
    INDEX idx_routing_type (routing_type),
    INDEX idx_is_active (is_active),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Правила маршрутизации между агентами';

-- ================================================================
-- ОБУЧАЮЩИЕ ДАННЫЕ И ЗНАНИЯ
-- ================================================================

-- ----------------------------------------------------------------
-- Таблица: agent_training_data
-- Описание: Обучающие данные для агентов
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_training_data (
    -- Первичный ключ
    training_id CHAR(36) PRIMARY KEY COMMENT 'UUID обучающих данных',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    
    -- Тип данных
    data_type ENUM('example', 'knowledge_base', 'faq', 'scenario', 'case_study') NOT NULL COMMENT 'Тип обучающих данных',
    category VARCHAR(100) COMMENT 'Категория данных',
    
    -- Данные
    title VARCHAR(500) NOT NULL COMMENT 'Заголовок',
    content TEXT NOT NULL COMMENT 'Содержимое',
    
    -- Структурированные данные для Few-Shot
    input_example TEXT COMMENT 'Пример входных данных',
    output_example TEXT COMMENT 'Пример выходных данных',
    
    -- Контекст
    tags JSON COMMENT 'Теги для поиска',
    context JSON COMMENT 'Контекст применения',
    
    -- Приоритет
    priority INTEGER DEFAULT 5 COMMENT 'Приоритет использования',
    
    -- Статус
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активны ли данные',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор данных',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_data_type (data_type),
    INDEX idx_category (category),
    INDEX idx_is_active (is_active),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Обучающие данные агентов';

-- ----------------------------------------------------------------
-- Таблица: agent_knowledge_base
-- Описание: База знаний агентов (RAG)
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_knowledge_base (
    -- Первичный ключ
    knowledge_id CHAR(36) PRIMARY KEY COMMENT 'UUID записи знаний',
    
    -- Связь с агентом
    agent_id CHAR(36) COMMENT 'UUID агента (NULL для общих знаний)',
    
    -- Знания
    title VARCHAR(500) NOT NULL COMMENT 'Заголовок',
    content TEXT NOT NULL COMMENT 'Содержимое знаний',
    source VARCHAR(500) COMMENT 'Источник знаний',
    
    -- Категоризация
    category VARCHAR(100) NOT NULL COMMENT 'Категория знаний',
    subcategory VARCHAR(100) COMMENT 'Подкатегория',
    tags JSON COMMENT 'Теги для поиска',
    
    -- Векторизация (для semantic search)
    embedding_vector JSON COMMENT 'Векторное представление (для RAG)',
    embedding_model VARCHAR(100) COMMENT 'Модель для эмбеддинга',
    
    -- Метрики использования
    access_count INTEGER DEFAULT 0 COMMENT 'Количество обращений',
    last_accessed_at TIMESTAMP COMMENT 'Последнее обращение',
    relevance_score DECIMAL(5,2) COMMENT 'Оценка релевантности',
    
    -- Статус
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активны ли знания',
    is_verified BOOLEAN DEFAULT FALSE COMMENT 'Проверены ли знания',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_category (category),
    INDEX idx_access_count (access_count),
    INDEX idx_last_accessed (last_accessed_at),
    INDEX idx_date (date),
    FULLTEXT INDEX idx_content_search (title, content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='База знаний агентов';

-- ================================================================
-- ОРГАНИЗАЦИОННАЯ СТРУКТУРА И РАЗВЕРТЫВАНИЕ
-- ================================================================

-- ----------------------------------------------------------------
-- Таблица: organizational_structure
-- Описание: Упрощенная организационная структура компании
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizational_structure (
    -- Первичный ключ
    id CHAR(36) PRIMARY KEY COMMENT 'UUID записи',
    
    -- Структура
    department VARCHAR(255) NOT NULL COMMENT 'Отдел (HR, IT, Finance, Sales)',
    position VARCHAR(255) NOT NULL COMMENT 'Должность',
    
    -- Сотрудник
    full_name VARCHAR(255) NOT NULL COMMENT 'ФИО сотрудника',
    
    -- Иерархия
    hierarchy_level INTEGER NOT NULL COMMENT 'Уровень иерархии (1 - топ менеджмент)',
    
    -- Связь с агентом
    agent_id CHAR(36) COMMENT 'UUID агента (если это AI-сотрудник)',
    
    -- Статус
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Активен ли сотрудник',
    employment_type ENUM('full_time', 'part_time', 'contract', 'ai_agent') DEFAULT 'full_time' COMMENT 'Тип занятости',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE SET NULL,
    
    -- Индексы
    INDEX idx_department (department),
    INDEX idx_hierarchy (hierarchy_level),
    INDEX idx_agent_id (agent_id),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Организационная структура';

-- ----------------------------------------------------------------
-- Таблица: deployed_agents_registry
-- Описание: Реестр развернутых агентов
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS deployed_agents_registry (
    -- Первичный ключ
    deployment_id CHAR(36) PRIMARY KEY COMMENT 'UUID развертывания',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    
    -- Идентификация на платформах
    telegram_bot_token VARCHAR(500) COMMENT 'Telegram Bot Token',
    telegram_username VARCHAR(255) COMMENT 'Telegram username',
    teams_app_id VARCHAR(255) COMMENT 'Microsoft Teams App ID',
    teams_bot_id VARCHAR(255) COMMENT 'Microsoft Teams Bot ID',
    slack_app_id VARCHAR(255) COMMENT 'Slack App ID',
    slack_bot_token VARCHAR(500) COMMENT 'Slack Bot Token',
    
    -- Роли в каналах
    channel_roles JSON COMMENT 'Роли в каналах (JSON)',
    
    -- Статус развертывания
    deployment_status ENUM('deployed', 'stopped', 'maintenance', 'error') DEFAULT 'deployed' COMMENT 'Статус развертывания',
    last_health_check TIMESTAMP COMMENT 'Последняя проверка здоровья',
    
    -- Лимиты и ограничения
    limits JSON COMMENT 'Лимиты (rate limits, quotas)',
    
    -- Метрики производительности
    performance_metrics JSON COMMENT 'Метрики производительности',
    last_activity TIMESTAMP COMMENT 'Последняя активность',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата развертывания',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Кто развернул',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_id (agent_id),
    INDEX idx_deployment_status (deployment_status),
    INDEX idx_last_activity (last_activity),
    INDEX idx_date (date),
    UNIQUE INDEX idx_telegram_username (telegram_username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Реестр развернутых агентов';

-- ================================================================
-- МЕТРИКИ И АНАЛИТИКА
-- ================================================================

-- ----------------------------------------------------------------
-- Таблица: agent_performance_metrics
-- Описание: Метрики производительности агентов
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_performance_metrics (
    -- Первичный ключ
    metric_id CHAR(36) PRIMARY KEY COMMENT 'UUID метрики',
    
    -- Связь с агентом
    agent_id CHAR(36) NOT NULL COMMENT 'UUID агента',
    
    -- Тип метрики
    metric_name VARCHAR(255) NOT NULL COMMENT 'Название метрики',
    metric_type ENUM('counter', 'gauge', 'histogram', 'rate') NOT NULL COMMENT 'Тип метрики',
    
    -- Значение
    metric_value DECIMAL(20,6) NOT NULL COMMENT 'Значение метрики',
    metric_unit VARCHAR(50) COMMENT 'Единица измерения',
    
    -- Временной период
    period ENUM('minute', 'hour', 'day', 'week', 'month') NOT NULL COMMENT 'Период метрики',
    period_start TIMESTAMP NOT NULL COMMENT 'Начало периода',
    period_end TIMESTAMP NOT NULL COMMENT 'Конец периода',
    
    -- Дополнительные данные
    dimensions JSON COMMENT 'Дополнительные измерения (tags)',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата записи',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_agent_metric (agent_id, metric_name),
    INDEX idx_period (period),
    INDEX idx_period_start (period_start),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Метрики производительности агентов';

-- ----------------------------------------------------------------
-- Таблица: system_metrics
-- Описание: Системные метрики
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_metrics (
    -- Первичный ключ
    id CHAR(36) PRIMARY KEY COMMENT 'UUID метрики',
    
    -- Метрика
    metric_name VARCHAR(255) NOT NULL COMMENT 'Название метрики',
    metric_value DECIMAL(20,6) NOT NULL COMMENT 'Значение',
    
    -- Связь с агентом (опционально)
    agent_id CHAR(36) COMMENT 'UUID агента (если применимо)',
    
    -- Период
    period VARCHAR(50) COMMENT 'Период (today, week, month, initialization)',
    
    -- Метаданные
    metadata JSON COMMENT 'Дополнительные данные',
    
    -- Аудит
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата записи',
    author VARCHAR(255) DEFAULT 'system' COMMENT 'Автор',
    
    -- Внешние ключи
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_metric_name (metric_name),
    INDEX idx_agent_metric (agent_id, metric_name),
    INDEX idx_period (period),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Системные метрики';

-- ================================================================
-- ПРЕДСТАВЛЕНИЯ (VIEWS)
-- ================================================================

-- ----------------------------------------------------------------
-- Представление: active_agents_view
-- Описание: Список активных агентов с основной информацией
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
-- Представление: agent_full_config_view
-- Описание: Полная конфигурация агента
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
-- ТРИГГЕРЫ
-- ================================================================

-- ----------------------------------------------------------------
-- Триггер: after_agent_update
-- Описание: Автоматическое создание записи в истории версий
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
-- Описание: Автоматическая очистка истекшей оперативной памяти
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
-- НАЧАЛЬНЫЕ ДАННЫЕ
-- ================================================================

-- Вставка системной метрики инициализации
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
-- ЗАВЕРШЕНИЕ
-- ================================================================

SELECT 'Workflow Office - Centralized Agent Database Schema v2.1 initialized successfully!' as status;
SELECT COUNT(*) as total_tables FROM information_schema.tables WHERE table_schema = 'office_services_agents';
