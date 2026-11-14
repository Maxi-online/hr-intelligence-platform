# 🏗️ Workflow Office - Structure of the Data Agency Database

## 📋 Contents
1. [Review](#review)
2. [Basic tables](#core tables)
3. [Memory tables (# Memory tables))
4. [History and logic](#logistics)
5. [Regulations and configurations](#rules-and-configurations)
6. [Learning data](#Learning data)
7. [Organization](#Organization)
8. [Metrics and Analysts] (#metrics-and-analytics)
9. [Linkages between tables](#communications between tables)
10. [Examples of requests](#examples of requests)

---

## 🎯 Overview

A centralized database for storing **all AI agents configurations**, their prompt, GPT settings, tools, memory and performance metrics.

### Key features:
- ✅ **Versionarity** - Full history of configuration changes
- ✅ **Modular** - separate storage of prompts, settings, tools
- ✅ **Core, Operational and Long-term Memory
- ✅ **Audit** - full logic of all agent actions
- ✅ **Scale** - support for unlimited number of agents
- ✅ **Flexibility** - JSON Castomic Data Fields

---

## 📊 Main tables

### 1. `agents` - Basic Table of Agents
**Destination:** Storage of basic information on each agent

| Field | Type | Description |
|------|-----|----------|
| `agent_id` | VARCHAR(255) PK | Unique ID agent (e.g: `supervisor_001`) |
| `agent_name` | VARCHAR(255) | Identified Name (e.g: `@boss.ai`) |
| `agent_type` | VARCHAR(100) | Type of agent (supervisor, recruiter, scrinner, menu) |
| `display_name` | VARCHAR(255) | Human name (e.g: "Alain Sergeyeva") |
| `role` | VARCHAR(255) | Role (Supervisor, Active Recruiter) |
| `persona` | TEXT | Brief description of the identity |
| `telegram_username` | VARCHAR(255) | Telegram username |
| `teams_identity` | VARCHAR(255) | Microsoft Teams identity |
| `status` | ENUM | active, inactive, maintenance, archived |
| `version` | VARCHAR(50) | The configuration version |

**Indexes:**
- PRIMARY KEY: `agent_id`
- INDEX: `agent_type`, `status`, `is_active`
- UNIQUE: `telegram_username`, `teams_identity`

---

### 2. `agent_prompts` - Prompts of agents
**Destination:** Storage of system prompts with versionarity

| Field | Type | Description |
|------|-----|----------|
| `prompt_id` | VARCHAR(255) PK | Unique ID Prompta |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `system_prompt` | TEXT | Main System Prompte |
| `tone_of_voice` | TEXT | Tone and style of communication |
| `version` | VARCHAR(50) | Prompt version |
| `is_current` | BOOLEAN | Current version |
| `examples` | JSON | Examples of dialogues (Few-Shot) |

** Specialities:**
- ✅ **Versonicity** - you can keep the history of all prompts
- ✅ **Reverse** - Easy to return to previous version
- ✅ **A/B testing** - comparison of different versions

---

### 3. `agent_gpt_settings` - GPT settings
**Purpose:** Model GPT configuration for each agent

| Field | Type | Description |
|------|-----|----------|
| `setting_id` | VARCHAR(255) PK | Unique ID Settings |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `model` | VARCHAR(100) | Model (gpt-5-nano, gpt-5, gpt-4.1) |
| `reasoning_effort` | ENUM | minimal, low, medium, high (GPT-5) |
| `temperature` | DECIMAL(3,2) | Temperature for GPT-4 |
| `max_tokens` | INTEGER | Max tokens in response |
| `tool_choice` | VARCHAR(50) | auto, required, none |
| `parallel_tool_calls` | BOOLEAN | Parallel challenges |
| `prompt_cache_enabled` | BOOLEAN | Kashing Prompt |

**Notes:**
- 🆕 **GPT-5** uses `reasoning_effort` instead of `temperature`
- 🚀 **Optimization** - Prompt caching and parallel tool calls
- ⚙️ **Flexible** - individual settings for each agent

---

### 4. `agent_tools` - Tools (Tools)
** Designation:** Catalogue of all available tools

| Field | Type | Description |
|------|-----|----------|
| `tool_id` | VARCHAR(255) PK | Unique ID instrument |
| `tool_name` | VARCHAR(255) | Name (search_resumes) |
| `tool_type` | ENUM | function, mcp, api, database |
| `description` | TEXT | Description for GPT |
| `parameters` | JSON | JSON parameter diagram |
| `mcp_server_url` | VARCHAR(500) | URL MCP servers |
| `api_endpoint` | VARCHAR(500) | Endpoint External API |

** Supported types:**
- 🔧 **function** - normal Python functions
- 🌐 **mcp** - MCP servers (e.g. DaData))
- 🔗 **api** - external REST API
- 💾 **database** = direct database requests

---

### 5. `agent_tools_mapping` - Contact of agents with instruments
**Purpose: ** What tools are available to each agent

| Field | Type | Description |
|------|-----|----------|
| `mapping_id` | VARCHAR(255) PK | Unique ID Communications |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `tool_id` | VARCHAR(255) FK | ID instrument |
| `is_enabled` | BOOLEAN | Do you have a tool on |
| `priority` | INTEGER | Priority (0 - Higher) |
| `custom_params` | JSON | Casto parameters |

---

## 🧠 Memory tables

### `core_memory` - Core memory
** Designation:** Critical rules and facts of the agent

| Field | Type | Description |
|------|-----|----------|
| `memory_id` | VARCHAR(255) PK | ID Memory records |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `memory_type` | ENUM | rule, fact, persona, constraint |
| `memory_key` | VARCHAR(255) | Key (response_language) |
| `memory_value` | TEXT | Value |
| `priority` | INTEGER | Priority (1-10) |
| `is_permanent` | BOOLEAN | Permanent memory |

**Examples of core memory:**
```sql
-- Language of replies
('mem_001', 'supervisor_001', 'rule', 'response_language', 'Always answer Russian', 1, TRUE)

-- Communication style
('mem_002', 'recruiter_001', 'persona', 'communication_style', 'Friendly, professional', 2, TRUE)

-- Limitations
('mem_003', 'scrinner_001', 'constraint', 'max_candidates_per_session', '10', 3, FALSE)
```

---

### `operational_memory` - Operating memory
** Designation: ** Context of current tasks and sessions

| Field | Type | Description |
|------|-----|----------|
| `operation_id` | VARCHAR(255) PK | ID Operations |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `session_id` | VARCHAR(255) | ID session |
| `user_id` | VARCHAR(255) | ID User |
| `task_context` | TEXT | Context of the task |
| `current_focus` | TEXT | Current Focus |
| `expires_at` | TIMESTAMP | Expiry date (TTL) |

** Specialities:**
- ⏰ **TTL** - Automatic removal after expiry
- 🔄 **Session** - linked to user session
- 📊 **Context** - Maintains the current status of the task

---

### `long_term_memory` - Long-term memory
** Designation:** Training and adaptation of the agent

| Field | Type | Description |
|------|-----|----------|
| `ltm_id` | VARCHAR(255) PK | ID Records |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `memory_type` | ENUM | learned_pattern, user_preference, success_case |
| `title` | VARCHAR(500) | Heading |
| `content` | TEXT | Content |
| `usage_count` | INTEGER | Number of applications |
| `success_rate` | DECIMAL(5,2) | Percentage of success |

** Examples:**
- 📈 **Learned Patterns** - identified behavioral patterns
- 👤 **User preferences** - user preferences
- ✅ **Communication cases** - successful briefcases
- ❌ **Failure cases** - failures (for training))

---

## 📜 History and logic

### 9. `chat_history` - chat history
** Designation:** Full history of all messages

| Field | Type | Description |
|------|-----|----------|
| `message_id` | VARCHAR(255) PK | ID Communications |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `session_id` | VARCHAR(255) | ID session |
| `role` | ENUM | user, assistant, system, tool |
| `content` | TEXT | Content |
| `tool_calls` | JSON | Challenges to tools |
| `platform` | ENUM | telegram, teams, slack, web |
| `tokens_used` | INTEGER | Token use |

---

### 10. `agent_activity_log` - Activity Log
** Designation:** Detailed logic of all actions

| Field | Type | Description |
|------|-----|----------|
| `log_id` | VARCHAR(255) PK | ID Loga |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `activity_type` | ENUM | message, tool_call, error, startup |
| `status` | ENUM | success, failure, partial |
| `duration_ms` | INTEGER | Length in ms |

---

### 11. `agent_version_history` - Version History
** Designation:** Tracking all configuration changes

| Field | Type | Description |
|------|-----|----------|
| `history_id` | VARCHAR(255) PK | ID Records |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `version` | VARCHAR(50) | Version |
| `change_type` | ENUM | prompt, settings, tools, full_config |
| `config_snapshot_before` | JSON | Snapshot before |
| `config_snapshot_after` | JSON | Snapshot after |

---

## ⚙️ Rules and configurations

### 12. `agent_rules` - Rules of conduct
** Designation: ** Rules to be followed by the agent

| Field | Type | Description |
|------|-----|----------|
| `rule_id` | VARCHAR(255) PK | ID Rules |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `rule_type` | ENUM | communication, behavior, security |
| `rule_content` | TEXT | Content of the rule |
| `priority` | INTEGER | Priority |

---

### 13. `agent_routing_rules` - Routine rules
** Designation:** How agents interact with each other

| Field | Type | Description |
|------|-----|----------|
| `routing_id` | VARCHAR(255) PK | ID Rules |
| `source_agent_id` | VARCHAR(255) FK | Agent Source |
| `target_agent_id` | VARCHAR(255) FK | Recipient Agent |
| `routing_type` | ENUM | delegation, escalation, collaboration |

** Example:**
```
supervisor_001 → recruiter_001 (delegation)
recruiter_001 → scrinner_001 (delegation)
scrinner_001 → supervisor_001 (report)
```

---

## 📚 Training data

### 14. `agent_training_data` - Training data
** Designation:**Few-Shot examples, scripts, briefcases

| Field | Type | Description |
|------|-----|----------|
| `training_id` | VARCHAR(255) PK | ID Data |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `data_type` | ENUM | example, knowledge_base, faq, scenario |
| `input_example` | TEXT | Example of entry |
| `output_example` | TEXT | Example of exit |

---

### 15. `agent_knowledge_base` - Knowledge base (RAG)
** Designation:** Semantic search and RAG

| Field | Type | Description |
|------|-----|----------|
| `knowledge_id` | VARCHAR(255) PK | ID knowledge |
| `agent_id` | VARCHAR(255) FK | ID agent (NULL for general) |
| `content` | TEXT | Content |
| `embedding_vector` | JSON | Vector view |
| `access_count` | INTEGER | Number of requests |

---

## 🏢 Organizational structure

### 16. `organizational_structure` - Structure
** Designation:** Hierarchy of company and AI agents

| Field | Type | Description |
|------|-----|----------|
| `id` | VARCHAR(255) PK | ID Records |
| `department` | VARCHAR(255) | Division (HR, IT, Finance) |
| `position` | VARCHAR(255) | Post |
| `full_name` | VARCHAR(255) | FIO |
| `hierarchy_level` | INTEGER | Level (1 - Top) |
| `agent_id` | VARCHAR(255) FK | ID agent (If AI) |

---

### 17. `deployed_agents_registry` - Deployment register
** Designation: ** Information on deployed agents

| Field | Type | Description |
|------|-----|----------|
| `deployment_id` | VARCHAR(255) PK | ID deployment |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `telegram_bot_token` | VARCHAR(500) | Telegram current |
| `deployment_status` | ENUM | deployed, stopped, maintenance |
| `last_health_check` | TIMESTAMP | Last check |

---

## 📈 Metro and analyst

### 18. `agent_performance_metrics` - Productivity metrics
** Designation:** Detailed agent performance metrics

| Field | Type | Description |
|------|-----|----------|
| `metric_id` | VARCHAR(255) PK | ID metrics |
| `agent_id` | VARCHAR(255) FK | ID agent |
| `metric_name` | VARCHAR(255) | The name of the metrics |
| `metric_value` | DECIMAL(20,6) | Value |
| `period` | ENUM | minute, hour, day, week, month |

** Examples of metrics:**
- 📊 `messages_processed' - Messages processed
- ⏱️ `avg_response_time' is the average response time
- 🔧 `tool_calls_count' is the number of tool calls
- ✅ `success_rate' is the percentage of successful requests
- 🎯 `user_satisfaction' - User satisfaction

---

### 19. `system_metrics` - System metrics
** Designation:** Common metrics of the system

| Field | Type | Description |
|------|-----|----------|
| `id` | VARCHAR(255) PK | ID metrics |
| `metric_name` | VARCHAR(255) | Name |
| `metric_value` | DECIMAL(20,6) | Value |
| `agent_id` | VARCHAR(255) FK | ID agent (optional) |

---

## 🔗 Links between tables

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

## 💡 Examples of requests

### Receive full agent configuration
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

### Recovering the core memory of the agent
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

### Agent statistics for the day
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

### History of Agent Change
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

### Productivity metrics per week
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

### Agents &apos; Interface Routes
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

## 🎨 Benefits of the structure

### ✅ Scale
- Unlimited number of agents
- Independent storage of components
- Horizontal scale

### ✅ Versionarity
- History of all changes
- Easy rebound to previous versions
- A/B configuration testing

### ✅ Flexible
- JSON Castomization Fields
- Modular architecture
- Easy addition of new types

### ✅ Productivity
- Indexes in all important fields
- Optimized submissions (views)
- Cashing of frequently used data

### ✅ Audit
- Full logic of action
- Productivity metrics
- History of change

---

## 🚀 Next steps

1. ** Data migration** - transfer of existing agents
2. **API interface** - creation of REST API for management
3. ** Web interface** - dashboard for administration
4. ** Monitoring** - Alert and Notification System
5. **Backapps** - Automatic backup

---

** Version:** 2.0.0  
**Date:** 2025-10-13  
**Audience:** Workflow Office Team

