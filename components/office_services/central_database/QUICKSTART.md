# 🚀 Workflow Office - Быстрый старт с базой данных

## 📦 Установка и инициализация

### 1. Создание базы данных
```bash
# MySQL
mysql -u root -p < complete_schema.sql

# PostgreSQL (если нужно)
psql -U postgres -f complete_schema_postgres.sql
```

### 2. Вставка примеров данных
```bash
mysql -u root -p office_services_agents < sample_data.sql
```

---

## 🔑 Основные операции

### Получить информацию об агенте
```sql
-- Базовая информация
SELECT * FROM agents WHERE agent_id = 'supervisor_001';

-- Полная конфигурация (используя VIEW)
SELECT * FROM agent_full_config_view WHERE agent_id = 'supervisor_001';
```

### Получить текущий промпт агента
```sql
SELECT 
    system_prompt,
    tone_of_voice,
    version
FROM agent_prompts
WHERE agent_id = 'supervisor_001' AND is_current = TRUE;
```

### Получить GPT настройки агента
```sql
SELECT 
    model,
    reasoning_effort,
    max_tokens,
    tool_choice,
    parallel_tool_calls
FROM agent_gpt_settings
WHERE agent_id = 'supervisor_001';
```

### Получить инструменты агента
```sql
SELECT 
    at.tool_name,
    at.description,
    at.tool_type,
    atm.is_enabled,
    atm.priority
FROM agent_tools_mapping atm
JOIN agent_tools at ON atm.tool_id = at.tool_id
WHERE atm.agent_id = 'supervisor_001'
ORDER BY atm.priority;
```

### Получить Core память агента
```sql
SELECT 
    memory_type,
    memory_key,
    memory_value,
    priority
FROM core_memory
WHERE agent_id = 'supervisor_001' 
    AND is_active = TRUE
ORDER BY priority;
```

---

## ➕ Создание нового агента

### 1. Создать базовую запись агента
```sql
INSERT INTO agents (
    agent_id, agent_name, agent_type, display_name, role, persona,
    telegram_username, status, version, date, author
) VALUES (
    UUID(), -- Автоматическая генерация UUID
    '@menu.ai',
    'menu',
    'Menu Assistant',
    'Restaurant Menu Expert',
    'Эксперт по меню ресторанов с передовыми техниками AI',
    '@demo_organization_menuaibot',
    'active',
    '1.0.0',
    CURRENT_TIMESTAMP,
    'admin'
);
```

### 2. Добавить промпт
```sql
INSERT INTO agent_prompts (
    prompt_id, agent_id, system_prompt, tone_of_voice, version, is_current
) VALUES (
    'prompt_menu_001_v1',
    'menu_agent_001',
    'Ты @menu.ai - эксперт по меню ресторанов...',
    'Дружелюбный, профессиональный, креативный',
    '1.0.0',
    TRUE
);
```

### 3. Настроить GPT
```sql
INSERT INTO agent_gpt_settings (
    setting_id, agent_id, model, reasoning_effort, 
    max_tokens, tool_choice, parallel_tool_calls
) VALUES (
    'gpt_menu_001',
    'menu_agent_001',
    'gpt-5-nano',
    'medium',
    4096,
    'auto',
    TRUE
);
```

### 4. Добавить инструменты
```sql
-- Связать существующий инструмент с агентом
INSERT INTO agent_tools_mapping (
    mapping_id, agent_id, tool_id, is_enabled, priority
) VALUES (
    'map_menu_search',
    'menu_agent_001',
    'tool_search_menu_items',
    TRUE,
    1
);
```

### 5. Добавить Core память
```sql
INSERT INTO core_memory (
    memory_id, agent_id, memory_type, memory_key, 
    memory_value, priority, is_permanent
) VALUES (
    'mem_menu_lang',
    'menu_agent_001',
    'rule',
    'response_language',
    'Всегда отвечай на русском языке',
    1,
    TRUE
);
```

---

## 🔄 Обновление конфигурации

### Обновить промпт (создать новую версию)
```sql
-- Снять флаг is_current со старой версии
UPDATE agent_prompts 
SET is_current = FALSE 
WHERE agent_id = 'supervisor_001' AND is_current = TRUE;

-- Добавить новую версию
INSERT INTO agent_prompts (
    prompt_id, agent_id, system_prompt, tone_of_voice, 
    version, is_current
) VALUES (
    'prompt_supervisor_001_v2',
    'supervisor_001',
    'Новый улучшенный промпт...',
    'Профессиональный руководитель',
    '2.0.0',
    TRUE
);
```

### Обновить GPT настройки
```sql
UPDATE agent_gpt_settings 
SET 
    reasoning_effort = 'high',
    max_tokens = 8192
WHERE agent_id = 'supervisor_001';
```

### Включить/выключить инструмент
```sql
UPDATE agent_tools_mapping 
SET is_enabled = FALSE 
WHERE agent_id = 'supervisor_001' 
    AND tool_id = 'tool_get_system_info';
```

---

## 📝 Логирование

### Записать сообщение в историю
```sql
INSERT INTO chat_history (
    message_id, agent_id, session_id, user_id, 
    role, content, platform, tokens_used, response_time_ms
) VALUES (
    UUID(),
    'supervisor_001',
    'session_12345',
    'user_67890',
    'assistant',
    'Отлично! Я начал поиск кандидатов...',
    'telegram',
    150,
    850
);
```

### Записать активность агента
```sql
INSERT INTO agent_activity_log (
    log_id, agent_id, activity_type, activity_name, 
    status, duration_ms
) VALUES (
    UUID(),
    'recruiter_001',
    'tool_call',
    'search_resumes',
    'success',
    1250
);
```

### Записать метрику
```sql
INSERT INTO agent_performance_metrics (
    metric_id, agent_id, metric_name, metric_type, 
    metric_value, period, period_start, period_end
) VALUES (
    UUID(),
    'supervisor_001',
    'messages_processed',
    'counter',
    45.0,
    'hour',
    NOW() - INTERVAL 1 HOUR,
    NOW()
);
```

---

## 📊 Аналитика

### Статистика сообщений за день
```sql
SELECT 
    agent_id,
    COUNT(*) as total_messages,
    AVG(tokens_used) as avg_tokens,
    AVG(response_time_ms) as avg_response_time,
    MAX(response_time_ms) as max_response_time
FROM chat_history
WHERE DATE(timestamp) = CURDATE()
    AND role = 'assistant'
GROUP BY agent_id;
```

### Топ используемых инструментов
```sql
SELECT 
    activity_name,
    COUNT(*) as usage_count,
    AVG(duration_ms) as avg_duration,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
    COUNT(CASE WHEN status = 'failure' THEN 1 END) as failure_count
FROM agent_activity_log
WHERE activity_type = 'tool_call'
    AND timestamp >= NOW() - INTERVAL 7 DAY
GROUP BY activity_name
ORDER BY usage_count DESC;
```

### Метрики производительности за неделю
```sql
SELECT 
    a.agent_name,
    m.metric_name,
    AVG(m.metric_value) as avg_value,
    MAX(m.metric_value) as max_value,
    MIN(m.metric_value) as min_value
FROM agent_performance_metrics m
JOIN agents a ON m.agent_id = a.agent_id
WHERE m.period_start >= NOW() - INTERVAL 7 DAY
GROUP BY a.agent_name, m.metric_name
ORDER BY a.agent_name, m.metric_name;
```

### История версий агента
```sql
SELECT 
    version,
    previous_version,
    change_type,
    changelog,
    changed_by,
    changed_at
FROM agent_version_history
WHERE agent_id = 'supervisor_001'
ORDER BY changed_at DESC
LIMIT 10;
```

---

## 🔍 Полезные запросы

### Список всех активных агентов
```sql
SELECT * FROM active_agents_view;
```

### Агенты с количеством инструментов
```sql
SELECT 
    a.agent_name,
    a.display_name,
    a.role,
    COUNT(atm.tool_id) as tools_count
FROM agents a
LEFT JOIN agent_tools_mapping atm ON a.agent_id = atm.agent_id 
    AND atm.is_enabled = TRUE
WHERE a.is_active = TRUE
GROUP BY a.agent_id;
```

### Маршруты взаимодействия агентов
```sql
SELECT 
    s.agent_name as from_agent,
    t.agent_name as to_agent,
    r.routing_type,
    r.routing_condition
FROM agent_routing_rules r
JOIN agents s ON r.source_agent_id = s.agent_id
JOIN agents t ON r.target_agent_id = t.agent_id
WHERE r.is_active = TRUE
ORDER BY r.priority;
```

### Оперативная память текущих сессий
```sql
SELECT 
    a.agent_name,
    om.session_id,
    om.user_id,
    om.task_type,
    om.current_focus,
    om.updated_at
FROM operational_memory om
JOIN agents a ON om.agent_id = a.agent_id
WHERE om.expires_at > NOW()
ORDER BY om.updated_at DESC;
```

---

## 🧹 Очистка и обслуживание

### Очистка истекшей оперативной памяти
```sql
DELETE FROM operational_memory
WHERE expires_at IS NOT NULL AND expires_at < NOW();
```

### Архивация старых сообщений (старше 30 дней)
```sql
-- Сначала создать архивную таблицу
CREATE TABLE chat_history_archive LIKE chat_history;

-- Перенести старые записи
INSERT INTO chat_history_archive
SELECT * FROM chat_history
WHERE timestamp < NOW() - INTERVAL 30 DAY;

-- Удалить из основной таблицы
DELETE FROM chat_history
WHERE timestamp < NOW() - INTERVAL 30 DAY;
```

### Очистка старых логов активности (старше 90 дней)
```sql
DELETE FROM agent_activity_log
WHERE timestamp < NOW() - INTERVAL 90 DAY;
```

---

## 🛠️ Python примеры

### Подключение к базе данных
```python
import mysql.connector
from typing import Dict, Any

class AgentDatabase:
    def __init__(self, config: Dict[str, Any]):
        self.connection = mysql.connector.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        self.cursor = self.connection.cursor(dictionary=True)
    
    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """Получить полную конфигурацию агента"""
        query = """
        SELECT 
            a.*,
            ap.system_prompt,
            ap.tone_of_voice,
            ags.model,
            ags.reasoning_effort,
            ags.max_tokens,
            ags.tool_choice
        FROM agents a
        LEFT JOIN agent_prompts ap ON a.agent_id = ap.agent_id AND ap.is_current = TRUE
        LEFT JOIN agent_gpt_settings ags ON a.agent_id = ags.agent_id
        WHERE a.agent_id = %s
        """
        self.cursor.execute(query, (agent_id,))
        return self.cursor.fetchone()
    
    def get_agent_tools(self, agent_id: str) -> list:
        """Получить инструменты агента"""
        query = """
        SELECT 
            at.tool_name,
            at.description,
            at.parameters,
            at.tool_type
        FROM agent_tools_mapping atm
        JOIN agent_tools at ON atm.tool_id = at.tool_id
        WHERE atm.agent_id = %s AND atm.is_enabled = TRUE
        ORDER BY atm.priority
        """
        self.cursor.execute(query, (agent_id,))
        return self.cursor.fetchall()
    
    def get_core_memory(self, agent_id: str) -> list:
        """Получить core память агента"""
        query = """
        SELECT 
            memory_type,
            memory_key,
            memory_value,
            priority
        FROM core_memory
        WHERE agent_id = %s AND is_active = TRUE
        ORDER BY priority
        """
        self.cursor.execute(query, (agent_id,))
        return self.cursor.fetchall()
    
    def log_message(self, agent_id: str, session_id: str, user_id: str,
                    role: str, content: str, platform: str, 
                    tokens_used: int = 0, response_time_ms: int = 0):
        """Записать сообщение в историю"""
        import uuid
        query = """
        INSERT INTO chat_history (
            message_id, agent_id, session_id, user_id,
            role, content, platform, tokens_used, response_time_ms
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (
            str(uuid.uuid4()), agent_id, session_id, user_id,
            role, content, platform, tokens_used, response_time_ms
        ))
        self.connection.commit()

# Использование
db = AgentDatabase({
    'host': 'localhost',
    'port': 3306,
    'user': 'office_services_user',
    'password': 'office_services_pass',
    'database': 'office_services_agents'
})

# Получить конфигурацию
config = db.get_agent_config('supervisor_001')
print(config)

# Получить инструменты
tools = db.get_agent_tools('supervisor_001')
print(tools)

# Получить память
memory = db.get_core_memory('supervisor_001')
print(memory)
```

---

## 🎯 Итоговый чеклист

### При создании нового агента:
- [ ] Создать запись в `agents`
- [ ] Добавить промпт в `agent_prompts`
- [ ] Настроить GPT в `agent_gpt_settings`
- [ ] Связать инструменты в `agent_tools_mapping`
- [ ] Добавить Core память в `core_memory`
- [ ] Добавить правила в `agent_rules`
- [ ] Настроить маршрутизацию в `agent_routing_rules`
- [ ] Добавить в оргструктуру `organizational_structure`
- [ ] Зарегистрировать развертывание в `deployed_agents_registry`

### При обновлении агента:
- [ ] Обновить версию в `agents`
- [ ] Создать новую версию промпта в `agent_prompts`
- [ ] Обновить настройки в `agent_gpt_settings` (если нужно)
- [ ] Записать изменения в `agent_version_history`

### Регулярное обслуживание:
- [ ] Очистка истекшей `operational_memory`
- [ ] Архивация старых `chat_history`
- [ ] Очистка старых `agent_activity_log`
- [ ] Анализ `agent_performance_metrics`
- [ ] Резервное копирование базы данных

---

**Автор:** Workflow Office Team  
**Версия:** 2.1.0  
**Дата:** 2025-10-13  
**Изменения:** UUID вместо VARCHAR, добавлены date/author

