# Agent Configuration and Memory Database

Schema and persistence reference for agent definitions, prompts, model settings, tool mappings, memory, conversations, routing rules, deployment records and metrics. It supports the shared supervisor/LLM service work; it is not a trained model or a complete autonomous-agent runtime.

## Files and database dialects

| File | Role |
| --- | --- |
| `docker-compose.yml` | Runtime database deployment configuration. |
| `init.sql` | Initialization script used by the runtime configuration. |
| `complete_schema.sql` | Expanded schema reference with MySQL-specific syntax. |
| `sample_data.sql` | Illustrative agent definitions and configuration examples. |
| `init_database.py` | Explicit initialization utility. |
| `migrate_agent_configs.py` | Explicit migration utility. |
| `DATABASE_STRUCTURE.md` | Table and field reference. |
| `DATABASE_DIAGRAM.md` | Mermaid schema diagrams. |
| `DATABASE_SCHEMA_ASCII.txt` | Text diagram. |
| `QUICKSTART.md` | Additional query/integration notes. |

The runtime service stack uses PostgreSQL. The expanded schema/reference also contains MySQL constructs such as `USE`, `AUTO_INCREMENT`, `GROUP_CONCAT` and MySQL-specific administrative commands. Do not apply that reference file to PostgreSQL as if it were a tested migration. Check the exact schema loaded by Compose and the columns expected by each service.

## Data model

The expanded reference groups agent metadata/prompts/model settings and tool catalogs/mappings; core, operational and long-term memory; conversation/activity/version history; behavioral/routing rules; few-shot/knowledge entries; organization/deployment records; and performance/system metrics. An `agent_training_data` table stores examples; its existence does not establish model fine-tuning. A tool catalog stores configuration; it does not execute a tool.

Operational-memory expiry, version fields and audit metadata are schema concepts. Automated retention, migration compatibility and concurrency behavior need checks against the chosen database engine and running services. A versioned prompt record should be traceable to the response generated with that version.

## Configuration and startup

Use the example settings and environment-variable names; supply credentials locally and choose an isolated demonstration database. Initialization utilities modify database state and are explicit operator actions. The public offline suite does not run them.

```bash
docker compose config --quiet
docker compose up -d
docker compose ps
docker compose logs --tail=100
```

Inspect Compose's database image, initialization mounts and persistent volume before starting it. Do not reuse an unrelated application's existing database volume. PostgreSQL and MySQL connection/driver examples must be kept with their respective schema dialects.

## Query examples from the expanded reference

The following read-only examples describe configuration lookup in the MySQL-oriented reference schema. Confirm table names and SQL dialect before using them against a runtime database.

```sql
-- Base connection
mysql -u office_services_user -p office_services_agents

-- Audit of tables
SHOW TABLES;

-- Screen of agents
SELECT * FROM active_agents_view;
```

```sql
-- Get an agent configuration
SELECT 
    a.agent_name,
    a.display_name,
    a.role,
    ap.system_prompt,
    ags.model,
    ags.reasoning_effort
FROM agents a
JOIN agent_prompts ap ON a.agent_id = ap.agent_id AND ap.is_current = TRUE
JOIN agent_gpt_settings ags ON a.agent_id = ags.agent_id
WHERE a.agent_id = 'supervisor_001';
```

```sql
-- Use VIEW
SELECT * FROM agent_full_config_view WHERE agent_id = 'supervisor_001';

-- Detailed request
SELECT 
    a.agent_name,
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

```sql
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb,
    table_rows
FROM information_schema.tables
WHERE table_schema = 'office_services_agents'
ORDER BY (data_length + index_length) DESC;
```

```sql
-- Agents &apos; messages
SELECT 
    a.agent_name,
    COUNT(*) as total_messages,
    AVG(ch.tokens_used) as avg_tokens,
    AVG(ch.response_time_ms) as avg_response_time
FROM chat_history ch
JOIN agents a ON ch.agent_id = a.agent_id
WHERE ch.timestamp >= NOW() - INTERVAL 7 DAY
GROUP BY a.agent_name
ORDER BY total_messages DESC;
```

```sql
SELECT * FROM agent_version_history 
WHERE agent_id = 'your_agent_id'
ORDER BY changed_at DESC;
```

## Python integration

Database adapters should use parameterized values for agent IDs and explicit transaction/connection handling. Keep credentials in the process environment or ignored local settings. Return only the fields required by the caller rather than copying raw conversations or secret settings into logs.

Validate configuration lookup, tool mappings, memory expiry, version selection and persistence using fictional records in a dedicated database. Verify that schema changes preserve the service contract before migrating an existing deployment. Retention and archival operations require an operator-defined policy; the source examples do not prove that archival tables or scheduled jobs exist in every runtime schema.

## Evaluation boundary

The root test suite validates candidate/ranking contracts, not these database migrations. No production records, backups, passwords or conversation histories are included. Data consistency, concurrent access, restore behavior and service/schema compatibility remain integration checks. See the shared-services and repository READMEs for component boundaries.
