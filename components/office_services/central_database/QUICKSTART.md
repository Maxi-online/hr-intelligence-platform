# 🚀 Workflow Office - Quick start with database



## 📦 Establishment and Initialization



### 1. Database development

```bash

# MySQL

mysql -u root -p < complete_schema.sql



# PostgreSQL (If necessary)

psql -U postgres -f complete_schema_postgres.sql

```



### 2. Box of data examples

```bash

mysql -u root -p office_services_agents < sample_data.sql

```



---



## 🔑 Main operations



### Get information on the agent.

```sql

-- Basic information

SELECT * FROM agents WHERE agent_id = 'supervisor_001';



-- Full configuration (using VIEW)

SELECT * FROM agent_full_config_view WHERE agent_id = 'supervisor_001';

```



### Get current agent prompt

```sql

SELECT 

    system_prompt,

    tone_of_voice,

    version

FROM agent_prompts

WHERE agent_id = 'supervisor_001' AND is_current = TRUE;

```



### Get an agent's GPT settings

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



### Get Agent's Tools

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



### Recover the Core Memory of the Agent

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



## ➕ Creation of a new agent



### 1. Create an agent &apos; s basic recording

```sql

INSERT INTO agents (

    agent_id, agent_name, agent_type, display_name, role, persona,

    telegram_username, status, version, date, author

) VALUES (

    UUID(), -- Automatic generation UUID

    '@menu.ai',

    'menu',

    'Menu Assistant',

    'Restaurant Menu Expert',

    'Expert on the menu of restaurants with advanced techniques AI',

    '@demo_organization_menuaibot',

    'active',

    '1.0.0',

    CURRENT_TIMESTAMP,

    'admin'

);

```



### 2. Add Prompt

```sql

INSERT INTO agent_prompts (

    prompt_id, agent_id, system_prompt, tone_of_voice, version, is_current

) VALUES (

    'prompt_menu_001_v1',

    'menu_agent_001',

    'You @menu.ai - Restaurant menu expert...',

    'Friendly, professional, creative',

    '1.0.0',

    TRUE

);

```



### 3. Settings GPT

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



### 4. Add Tools

```sql

-- Link the existing tool to the agent

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



### 5. Add Core Memory

```sql

INSERT INTO core_memory (

    memory_id, agent_id, memory_type, memory_key, 

    memory_value, priority, is_permanent

) VALUES (

    'mem_menu_lang',

    'menu_agent_001',

    'rule',

    'response_language',

    'Always answer in Russian.',

    1,

    TRUE

);

```



---



## 🔄 Upgrade configuration



### Update Prompte (create a new version)

```sql

-- Remove the flag is_current From the old version

UPDATE agent_prompts 

SET is_current = FALSE 

WHERE agent_id = 'supervisor_001' AND is_current = TRUE;



-- Add a new version

INSERT INTO agent_prompts (

    prompt_id, agent_id, system_prompt, tone_of_voice, 

    version, is_current

) VALUES (

    'prompt_supervisor_001_v2',

    'supervisor_001',

    'New Enhanced Prompte...',

    'Professional Manager',

    '2.0.0',

    TRUE

);

```



### Update GPT settings

```sql

UPDATE agent_gpt_settings 

SET 

    reasoning_effort = 'high',

    max_tokens = 8192

WHERE agent_id = 'supervisor_001';

```



### Activate/ Disable tool

```sql

UPDATE agent_tools_mapping 

SET is_enabled = FALSE 

WHERE agent_id = 'supervisor_001' 

    AND tool_id = 'tool_get_system_info';

```



---



## 📝 Logging



### Write a message into history

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

    'Great! I started looking for candidates...',

    'telegram',

    150,

    850

);

```



### Record agent activity

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



### Write down the metric

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



## 📊 Analytics



### Daily message statistics

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



### Top of tools used

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



### Productivity metrics per week

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



### Agent's Version History

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



## 🔍 Useful Requests



### List of all active agents

```sql

SELECT * FROM active_agents_view;

```



### Agents with number of tools

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



### Agents &apos; Interface Routes

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



### Memory of current sessions

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



## 🧹 Cleaning and maintenance



### Cleaning of exhausted memory

```sql

DELETE FROM operational_memory

WHERE expires_at IS NOT NULL AND expires_at < NOW();

```



### Archiving of old messages (over 30 days)

```sql

-- First create an archive table

CREATE TABLE chat_history_archive LIKE chat_history;



-- Move old records

INSERT INTO chat_history_archive

SELECT * FROM chat_history

WHERE timestamp < NOW() - INTERVAL 30 DAY;



-- Remove from Main Table

DELETE FROM chat_history

WHERE timestamp < NOW() - INTERVAL 30 DAY;

```



### Cleaning of old activity logs (over 90 days)

```sql

DELETE FROM agent_activity_log

WHERE timestamp < NOW() - INTERVAL 90 DAY;

```



---



## 🛠️ Python Examples



### Connecting to the database

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

        """Receive full agent configuration"""

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

        """Get Agents Tools"""

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

        """Get core Agent memory"""

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

        """Write a message into history"""

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



# Use

db = AgentDatabase({

    'host': 'localhost',

    'port': 3306,

    'user': 'office_services_user',

    'password': 'office_services_pass',

    'database': 'office_services_agents'

})



# Get configuration

config = db.get_agent_config('supervisor_001')

print(config)



# Get Tools

tools = db.get_agent_tools('supervisor_001')

print(tools)



# Get a memory

memory = db.get_core_memory('supervisor_001')

print(memory)

```



---



## 🎯 Final Cheflist



### When creating a new agent:

- [ ] Create an entry in `agents`

- [ ] Add prop to `agent_prompts`

- [ ] Adjust GPT in `agent_gpt_settings`

- [ ] Link the tools to `agent_tools_mapping`

- [ ] Add Core memory to `core_memory`

- [ ] Add rules to `agent_rules`

- [ ] Set the route in `agent_routing_rules`

- [ ] Add `organizational_structure` to the structure

- [ ] Record deployment to `deployed_agents_registry`



### When updating the agent:

- [ ] Update version of `agents`

- [ ] Create a new version of the `agent_prompts` prompt

- [ ] Update settings in `agent_gpt_settings` (if necessary))

- [ ] Write down changes to `agent_version_history`



### Regular services:

- [ ] Clean-up of the expired `operational_memory`

- [ ] Archiving old `chat_history`

- [ ] Cleaning old `agent_activity_log`

- [ ] Analysis of `agent_performance_metrics`

- [ ] Back-up database



---



**Audience:** Workflow Office Team  

** Version:** 2.1.0  

**Date:** 2025-10-13  

**Changes:** UUID instead of VARCHAR, added Data/autor



