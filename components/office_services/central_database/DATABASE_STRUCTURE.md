# 🏗️ Workflow Office - Структура Базы Данных Агентов

## 📋 Оглавление
1. [Обзор](#обзор)
2. [Основные таблицы](#основные-таблицы)
3. [Таблицы памяти](#таблицы-памяти)
4. [История и логирование](#история-и-логирование)
5. [Правила и конфигурации](#правила-и-конфигурации)
6. [Обучающие данные](#обучающие-данные)
7. [Организационная структура](#организационная-структура)
8. [Метрики и аналитика](#метрики-и-аналитика)
9. [Связи между таблицами](#связи-между-таблицами)
10. [Примеры запросов](#примеры-запросов)

---

## 🎯 Обзор

Централизованная база данных для хранения **всех конфигураций AI-агентов**, их промптов, настроек GPT, инструментов, памяти и метрик производительности.

### Ключевые особенности:
- ✅ **Версионность** - полная история изменений конфигураций
- ✅ **Модульность** - раздельное хранение промптов, настроек, инструментов
- ✅ **Память** - Core, Operational и Long-term память
- ✅ **Аудит** - полное логирование всех действий агентов
- ✅ **Масштабируемость** - поддержка неограниченного количества агентов
- ✅ **Гибкость** - JSON поля для кастомных данных

---

## 📊 Основные таблицы

### 1. `agents` - Основная таблица агентов
**Назначение:** Хранение базовой информации о каждом агенте

| Поле | Тип | Описание |
|------|-----|----------|
| `agent_id` | VARCHAR(255) PK | Уникальный ID агента (например: `supervisor_001`) |
| `agent_name` | VARCHAR(255) | Отображаемое имя (например: `@boss.ai`) |
| `agent_type` | VARCHAR(100) | Тип агента (supervisor, recruiter, scrinner, menu) |
| `display_name` | VARCHAR(255) | Человеческое имя (например: "Алена Сергеева") |
| `role` | VARCHAR(255) | Роль (Supervisor, Active Recruiter) |
| `persona` | TEXT | Краткое описание личности |
| `telegram_username` | VARCHAR(255) | Telegram username |
| `teams_identity` | VARCHAR(255) | Microsoft Teams identity |
| `status` | ENUM | active, inactive, maintenance, archived |
| `version` | VARCHAR(50) | Версия конфигурации |

**Индексы:**
- PRIMARY KEY: `agent_id`
- INDEX: `agent_type`, `status`, `is_active`
- UNIQUE: `telegram_username`, `teams_identity`

---

### 2. `agent_prompts` - Промпты агентов
**Назначение:** Хранение системных промптов с версионностью

| Поле | Тип | Описание |
|------|-----|----------|
| `prompt_id` | VARCHAR(255) PK | Уникальный ID промпта |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `system_prompt` | TEXT | Основной системный промпт |
| `tone_of_voice` | TEXT | Тон и стиль общения |
| `version` | VARCHAR(50) | Версия промпта |
| `is_current` | BOOLEAN | Текущая версия |
| `examples` | JSON | Примеры диалогов (Few-Shot) |

**Особенности:**
- ✅ **Версионность** - можно хранить историю всех промптов
- ✅ **Откат** - легко вернуться к предыдущей версии
- ✅ **A/B тестирование** - сравнение разных версий

---

### 3. `agent_gpt_settings` - Настройки GPT
**Назначение:** Конфигурация GPT модели для каждого агента

| Поле | Тип | Описание |
|------|-----|----------|
| `setting_id` | VARCHAR(255) PK | Уникальный ID настройки |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `model` | VARCHAR(100) | Модель (gpt-5-nano, gpt-5, gpt-4.1) |
| `reasoning_effort` | ENUM | minimal, low, medium, high (GPT-5) |
| `temperature` | DECIMAL(3,2) | Temperature для GPT-4 |
| `max_tokens` | INTEGER | Макс. токенов в ответе |
| `tool_choice` | VARCHAR(50) | auto, required, none |
| `parallel_tool_calls` | BOOLEAN | Параллельные вызовы |
| `prompt_cache_enabled` | BOOLEAN | Кеширование промпта |

**Примечания:**
- 🆕 **GPT-5** использует `reasoning_effort` вместо `temperature`
- 🚀 **Оптимизация** - prompt caching и параллельные tool calls
- ⚙️ **Гибкость** - индивидуальные настройки для каждого агента

---

### 4. `agent_tools` - Инструменты (Tools)
**Назначение:** Каталог всех доступных инструментов

| Поле | Тип | Описание |
|------|-----|----------|
| `tool_id` | VARCHAR(255) PK | Уникальный ID инструмента |
| `tool_name` | VARCHAR(255) | Название (search_resumes) |
| `tool_type` | ENUM | function, mcp, api, database |
| `description` | TEXT | Описание для GPT |
| `parameters` | JSON | JSON схема параметров |
| `mcp_server_url` | VARCHAR(500) | URL MCP сервера |
| `api_endpoint` | VARCHAR(500) | Endpoint внешнего API |

**Поддерживаемые типы:**
- 🔧 **function** - обычные Python функции
- 🌐 **mcp** - MCP серверы (например, DaData)
- 🔗 **api** - внешние REST API
- 💾 **database** - прямые запросы к БД

---

### 5. `agent_tools_mapping` - Связь агентов с инструментами
**Назначение:** Какие инструменты доступны каждому агенту

| Поле | Тип | Описание |
|------|-----|----------|
| `mapping_id` | VARCHAR(255) PK | Уникальный ID связи |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `tool_id` | VARCHAR(255) FK | ID инструмента |
| `is_enabled` | BOOLEAN | Включен ли инструмент |
| `priority` | INTEGER | Приоритет (0 - высший) |
| `custom_params` | JSON | Кастомные параметры |

---

## 🧠 Таблицы памяти

### 6. `core_memory` - Core память
**Назначение:** Критически важные правила и факты агента

| Поле | Тип | Описание |
|------|-----|----------|
| `memory_id` | VARCHAR(255) PK | ID записи памяти |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `memory_type` | ENUM | rule, fact, persona, constraint |
| `memory_key` | VARCHAR(255) | Ключ (response_language) |
| `memory_value` | TEXT | Значение |
| `priority` | INTEGER | Приоритет (1-10) |
| `is_permanent` | BOOLEAN | Постоянная память |

**Примеры core памяти:**
```sql
-- Язык ответов
('mem_001', 'supervisor_001', 'rule', 'response_language', 'Всегда отвечай на русском', 1, TRUE)

-- Стиль общения
('mem_002', 'recruiter_001', 'persona', 'communication_style', 'Дружелюбная, профессиональная', 2, TRUE)

-- Ограничения
('mem_003', 'scrinner_001', 'constraint', 'max_candidates_per_session', '10', 3, FALSE)
```

---

### 7. `operational_memory` - Оперативная память
**Назначение:** Контекст текущих задач и сессий

| Поле | Тип | Описание |
|------|-----|----------|
| `operation_id` | VARCHAR(255) PK | ID операции |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `session_id` | VARCHAR(255) | ID сессии |
| `user_id` | VARCHAR(255) | ID пользователя |
| `task_context` | TEXT | Контекст задачи |
| `current_focus` | TEXT | Текущий фокус |
| `expires_at` | TIMESTAMP | Срок истечения (TTL) |

**Особенности:**
- ⏰ **TTL** - автоматическое удаление по истечении срока
- 🔄 **Сессионная** - привязана к сессии пользователя
- 📊 **Контекст** - хранит текущее состояние задачи

---

### 8. `long_term_memory` - Долговременная память
**Назначение:** Обучение и адаптация агента

| Поле | Тип | Описание |
|------|-----|----------|
| `ltm_id` | VARCHAR(255) PK | ID записи |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `memory_type` | ENUM | learned_pattern, user_preference, success_case |
| `title` | VARCHAR(500) | Заголовок |
| `content` | TEXT | Содержимое |
| `usage_count` | INTEGER | Количество применений |
| `success_rate` | DECIMAL(5,2) | Процент успеха |

**Примеры:**
- 📈 **Learned patterns** - выявленные паттерны поведения
- 👤 **User preferences** - предпочтения пользователей
- ✅ **Success cases** - успешные кейсы
- ❌ **Failure cases** - неудачные случаи (для обучения)

---

## 📜 История и логирование

### 9. `chat_history` - История чатов
**Назначение:** Полная история всех сообщений

| Поле | Тип | Описание |
|------|-----|----------|
| `message_id` | VARCHAR(255) PK | ID сообщения |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `session_id` | VARCHAR(255) | ID сессии |
| `role` | ENUM | user, assistant, system, tool |
| `content` | TEXT | Содержимое |
| `tool_calls` | JSON | Вызовы инструментов |
| `platform` | ENUM | telegram, teams, slack, web |
| `tokens_used` | INTEGER | Использовано токенов |

---

### 10. `agent_activity_log` - Лог активности
**Назначение:** Детальное логирование всех действий

| Поле | Тип | Описание |
|------|-----|----------|
| `log_id` | VARCHAR(255) PK | ID лога |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `activity_type` | ENUM | message, tool_call, error, startup |
| `status` | ENUM | success, failure, partial |
| `duration_ms` | INTEGER | Длительность в мс |

---

### 11. `agent_version_history` - История версий
**Назначение:** Отслеживание всех изменений конфигурации

| Поле | Тип | Описание |
|------|-----|----------|
| `history_id` | VARCHAR(255) PK | ID записи |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `version` | VARCHAR(50) | Версия |
| `change_type` | ENUM | prompt, settings, tools, full_config |
| `config_snapshot_before` | JSON | Снапшот до |
| `config_snapshot_after` | JSON | Снапшот после |

---

## ⚙️ Правила и конфигурации

### 12. `agent_rules` - Правила поведения
**Назначение:** Правила, которым должен следовать агент

| Поле | Тип | Описание |
|------|-----|----------|
| `rule_id` | VARCHAR(255) PK | ID правила |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `rule_type` | ENUM | communication, behavior, security |
| `rule_content` | TEXT | Содержимое правила |
| `priority` | INTEGER | Приоритет |

---

### 13. `agent_routing_rules` - Правила маршрутизации
**Назначение:** Как агенты взаимодействуют между собой

| Поле | Тип | Описание |
|------|-----|----------|
| `routing_id` | VARCHAR(255) PK | ID правила |
| `source_agent_id` | VARCHAR(255) FK | Агент-источник |
| `target_agent_id` | VARCHAR(255) FK | Агент-получатель |
| `routing_type` | ENUM | delegation, escalation, collaboration |

**Пример:**
```
supervisor_001 → recruiter_001 (delegation)
recruiter_001 → scrinner_001 (delegation)
scrinner_001 → supervisor_001 (report)
```

---

## 📚 Обучающие данные

### 14. `agent_training_data` - Обучающие данные
**Назначение:** Few-Shot примеры, сценарии, кейсы

| Поле | Тип | Описание |
|------|-----|----------|
| `training_id` | VARCHAR(255) PK | ID данных |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `data_type` | ENUM | example, knowledge_base, faq, scenario |
| `input_example` | TEXT | Пример входа |
| `output_example` | TEXT | Пример выхода |

---

### 15. `agent_knowledge_base` - База знаний (RAG)
**Назначение:** Семантический поиск и RAG

| Поле | Тип | Описание |
|------|-----|----------|
| `knowledge_id` | VARCHAR(255) PK | ID знаний |
| `agent_id` | VARCHAR(255) FK | ID агента (NULL для общих) |
| `content` | TEXT | Содержимое |
| `embedding_vector` | JSON | Векторное представление |
| `access_count` | INTEGER | Количество обращений |

---

## 🏢 Организационная структура

### 16. `organizational_structure` - Оргструктура
**Назначение:** Иерархия компании и AI-агентов

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | VARCHAR(255) PK | ID записи |
| `department` | VARCHAR(255) | Отдел (HR, IT, Finance) |
| `position` | VARCHAR(255) | Должность |
| `full_name` | VARCHAR(255) | ФИО |
| `hierarchy_level` | INTEGER | Уровень (1 - топ) |
| `agent_id` | VARCHAR(255) FK | ID агента (если AI) |

---

### 17. `deployed_agents_registry` - Реестр развертывания
**Назначение:** Информация о развернутых агентах

| Поле | Тип | Описание |
|------|-----|----------|
| `deployment_id` | VARCHAR(255) PK | ID развертывания |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `telegram_bot_token` | VARCHAR(500) | Telegram токен |
| `deployment_status` | ENUM | deployed, stopped, maintenance |
| `last_health_check` | TIMESTAMP | Последняя проверка |

---

## 📈 Метрики и аналитика

### 18. `agent_performance_metrics` - Метрики производительности
**Назначение:** Детальные метрики работы агентов

| Поле | Тип | Описание |
|------|-----|----------|
| `metric_id` | VARCHAR(255) PK | ID метрики |
| `agent_id` | VARCHAR(255) FK | ID агента |
| `metric_name` | VARCHAR(255) | Название метрики |
| `metric_value` | DECIMAL(20,6) | Значение |
| `period` | ENUM | minute, hour, day, week, month |

**Примеры метрик:**
- 📊 `messages_processed` - обработано сообщений
- ⏱️ `avg_response_time` - среднее время ответа
- 🔧 `tool_calls_count` - количество вызовов инструментов
- ✅ `success_rate` - процент успешных запросов
- 🎯 `user_satisfaction` - удовлетворенность пользователей

---

### 19. `system_metrics` - Системные метрики
**Назначение:** Общие метрики системы

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | VARCHAR(255) PK | ID метрики |
| `metric_name` | VARCHAR(255) | Название |
| `metric_value` | DECIMAL(20,6) | Значение |
| `agent_id` | VARCHAR(255) FK | ID агента (опционально) |

---

## 🔗 Связи между таблицами

```
┌─────────────────┐
│     agents      │◄─────┐
└────────┬────────┘      │
         │               │
         ├──────────────►│ agent_prompts
         │               │
         ├──────────────►│ agent_gpt_settings
         │               │
         ├──────────────►│ agent_tools_mapping ◄──► agent_tools
         │               │
         ├──────────────►│ core_memory
         │               │
         ├──────────────►│ operational_memory
         │               │
         ├──────────────►│ long_term_memory
         │               │
         ├──────────────►│ chat_history
         │               │
         ├──────────────►│ agent_activity_log
         │               │
         ├──────────────►│ agent_version_history
         │               │
         ├──────────────►│ agent_rules
         │               │
         ├──────────────►│ agent_routing_rules (source & target)
         │               │
         ├──────────────►│ agent_training_data
         │               │
         ├──────────────►│ agent_knowledge_base
         │               │
         ├──────────────►│ deployed_agents_registry
         │               │
         └──────────────►│ agent_performance_metrics
```

---

## 💡 Примеры запросов

### Получить полную конфигурацию агента
```sql
SELECT 
    a.agent_id,
    a.agent_name,
    a.display_name,
    ap.system_prompt,
    ags.model,
    ags.reasoning_effort,
    GROUP_CONCAT(at.tool_name) as tools
FROM agents a
LEFT JOIN agent_prompts ap ON a.agent_id = ap.agent_id AND ap.is_current = TRUE
LEFT JOIN agent_gpt_settings ags ON a.agent_id = ags.agent_id
LEFT JOIN agent_tools_mapping atm ON a.agent_id = atm.agent_id AND atm.is_enabled = TRUE
LEFT JOIN agent_tools at ON atm.tool_id = at.tool_id
WHERE a.agent_id = 'supervisor_001'
GROUP BY a.agent_id;
```

### Получить core память агента
```sql
SELECT 
    memory_key,
    memory_value,
    memory_type,
    priority
FROM core_memory
WHERE agent_id = 'supervisor_001'
    AND is_active = TRUE
ORDER BY priority ASC;
```

### Статистика по агенту за день
```sql
SELECT 
    COUNT(*) as total_messages,
    AVG(tokens_used) as avg_tokens,
    AVG(response_time_ms) as avg_response_time
FROM chat_history
WHERE agent_id = 'recruiter_001'
    AND DATE(timestamp) = CURDATE()
    AND role = 'assistant';
```

### История изменений агента
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

### Метрики производительности за неделю
```sql
SELECT 
    metric_name,
    AVG(metric_value) as avg_value,
    MAX(metric_value) as max_value,
    MIN(metric_value) as min_value
FROM agent_performance_metrics
WHERE agent_id = 'scrinner_001'
    AND period = 'day'
    AND period_start >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY metric_name;
```

### Маршруты взаимодействия агентов
```sql
SELECT 
    s.agent_name as source_agent,
    t.agent_name as target_agent,
    r.routing_type,
    r.is_active
FROM agent_routing_rules r
JOIN agents s ON r.source_agent_id = s.agent_id
JOIN agents t ON r.target_agent_id = t.agent_id
WHERE r.is_active = TRUE
ORDER BY s.agent_name, r.priority;
```

---

## 🎨 Преимущества структуры

### ✅ Масштабируемость
- Неограниченное количество агентов
- Независимое хранение компонентов
- Горизонтальное масштабирование

### ✅ Версионность
- История всех изменений
- Легкий откат к предыдущим версиям
- A/B тестирование конфигураций

### ✅ Гибкость
- JSON поля для кастомизации
- Модульная архитектура
- Легкое добавление новых типов

### ✅ Производительность
- Индексы на всех важных полях
- Оптимизированные представления (views)
- Кеширование часто используемых данных

### ✅ Аудит
- Полное логирование действий
- Метрики производительности
- История изменений

---

## 🚀 Следующие шаги

1. **Миграция данных** - перенос существующих агентов
2. **API интерфейс** - создание REST API для управления
3. **Веб-интерфейс** - dashboard для администрирования
4. **Мониторинг** - система алертов и уведомлений
5. **Бэкапы** - автоматическое резервное копирование

---

**Версия:** 2.0.0  
**Дата:** 2025-10-13  
**Автор:** Workflow Office Team

