# 🗂️ Workflow Office - Database Figures

## 📊 Entity Relationship Diagram (ERD)

### Full database diagram

```mermaid
erDiagram
    %% ============================================
    %% MAIN TABLES OF AGENCIES
    %% ============================================
    
    agents {
        VARCHAR agent_id PK "Unique ID agent"
        VARCHAR agent_name "Identified Name"
        VARCHAR agent_type "Type of agent"
        VARCHAR display_name "Human name"
        VARCHAR role "The role of the agent"
        TEXT persona "Identity description"
        VARCHAR telegram_username UK "Telegram username"
        VARCHAR teams_identity UK "Teams identity"
        ENUM status "active/inactive/maintenance"
        VARCHAR version "The configuration version"
        BOOLEAN is_active "Activated"
        TIMESTAMP created_at
        TIMESTAMP updated_at
        JSON metadata "Metadata"
    }
    
    agent_prompts {
        VARCHAR prompt_id PK "ID Prompta"
        VARCHAR agent_id FK "ID agent"
        TEXT system_prompt "System Prompte"
        TEXT tone_of_voice "Tone of communication"
        VARCHAR version "Prompt version"
        BOOLEAN is_current "Current version"
        TEXT additional_instructions
        JSON examples "Few-Shot Examples"
        TIMESTAMP created_at
        TEXT changelog "Description of changes"
    }
    
    agent_gpt_settings {
        VARCHAR setting_id PK "ID Settings"
        VARCHAR agent_id FK UK "ID agent"
        VARCHAR model "gpt-5-nano/gpt-5"
        ENUM reasoning_effort "minimal/low/medium/high"
        DECIMAL temperature "Temperature for GPT-4"
        INTEGER max_tokens "Max Tokenov"
        VARCHAR tool_choice "auto/required/none"
        BOOLEAN parallel_tool_calls
        BOOLEAN prompt_cache_enabled
        VARCHAR prompt_cache_key
        BOOLEAN use_responses_api
        INTEGER rate_limit_per_minute
    }
    
    agent_tools {
        VARCHAR tool_id PK "ID instrument"
        VARCHAR tool_name UK "Title of tool"
        ENUM tool_type "function/mcp/api/database"
        TEXT description "Description for GPT"
        VARCHAR category "Category"
        JSON parameters "JSON parameter diagram"
        VARCHAR mcp_server_url "URL MCP servers"
        VARCHAR api_endpoint "API endpoint"
        BOOLEAN is_active
    }
    
    agent_tools_mapping {
        VARCHAR mapping_id PK "ID Communications"
        VARCHAR agent_id FK "ID agent"
        VARCHAR tool_id FK "ID instrument"
        BOOLEAN is_enabled "Whether included"
        INTEGER priority "Priority (0-Higher)"
        INTEGER rate_limit_per_hour
        JSON custom_params
    }
    
    %% ============================================
    %% AGENT MEMORY
    %% ============================================
    
    core_memory {
        VARCHAR memory_id PK "ID Memory records"
        VARCHAR agent_id FK "ID agent"
        ENUM memory_type "rule/fact/persona/constraint"
        VARCHAR memory_category
        VARCHAR memory_key "The Key to Memory"
        TEXT memory_value "Value"
        INTEGER priority "Priority 1-10"
        BOOLEAN is_permanent "Permanent memory"
        BOOLEAN is_active
        JSON applies_to_context
        JSON tags
    }
    
    operational_memory {
        VARCHAR operation_id PK "ID Operations"
        VARCHAR agent_id FK "ID agent"
        VARCHAR session_id "ID session"
        VARCHAR user_id "ID User"
        VARCHAR task_type "Type of task"
        TEXT task_context "Context"
        TEXT current_focus "Current Focus"
        JSON session_data
        TIMESTAMP expires_at "TTL"
        TIMESTAMP created_at
    }
    
    long_term_memory {
        VARCHAR ltm_id PK "ID Records"
        VARCHAR agent_id FK "ID agent"
        ENUM memory_type "learned_pattern/user_preference"
        VARCHAR title
        TEXT content
        JSON context_tags
        INTEGER usage_count "Number of applications"
        DECIMAL success_rate "Percentage of success"
        TIMESTAMP last_used_at
        BOOLEAN is_active
    }
    
    %% ============================================
    %% BACKGROUND AND LOIGRATION
    %% ============================================
    
    chat_history {
        VARCHAR message_id PK "ID Communications"
        VARCHAR agent_id FK "ID agent"
        VARCHAR session_id "ID session"
        VARCHAR user_id "ID User"
        ENUM role "user/assistant/system/tool"
        TEXT content "Content"
        ENUM content_type "text/image/tool_call"
        JSON tool_calls "Challenges to tools"
        ENUM platform "telegram/teams/slack"
        INTEGER tokens_used
        INTEGER response_time_ms
        TIMESTAMP timestamp
    }
    
    agent_activity_log {
        VARCHAR log_id PK "ID Loga"
        VARCHAR agent_id FK "ID agent"
        ENUM activity_type "message/tool_call/error"
        VARCHAR activity_name
        TEXT description
        JSON details
        ENUM status "success/failure/partial"
        TEXT error_message
        INTEGER duration_ms
        TIMESTAMP timestamp
    }
    
    agent_version_history {
        VARCHAR history_id PK "ID History"
        VARCHAR agent_id FK "ID agent"
        VARCHAR version "Version"
        VARCHAR previous_version
        ENUM change_type "prompt/settings/tools"
        TEXT changelog
        JSON config_snapshot_before
        JSON config_snapshot_after
        VARCHAR changed_by
        BOOLEAN is_rollback
        TIMESTAMP changed_at
    }
    
    %% ============================================
    %% RULES AND CONFIGURES
    %% ============================================
    
    agent_rules {
        VARCHAR rule_id PK "ID Rules"
        VARCHAR agent_id FK "ID agent"
        ENUM rule_type "communication/behavior/security"
        VARCHAR rule_name
        TEXT rule_content
        JSON applies_when
        INTEGER priority
        BOOLEAN is_active
        BOOLEAN is_overridable
    }
    
    agent_routing_rules {
        VARCHAR routing_id PK "ID Rules"
        VARCHAR source_agent_id FK "Agent Source"
        VARCHAR target_agent_id FK "Recipient Agent"
        ENUM routing_type "delegation/escalation/report"
        TEXT routing_condition
        BOOLEAN is_bidirectional
        INTEGER priority
        BOOLEAN is_active
    }
    
    %% ============================================
    %% DATA TRAINING
    %% ============================================
    
    agent_training_data {
        VARCHAR training_id PK "ID training data"
        VARCHAR agent_id FK "ID agent"
        ENUM data_type "example/knowledge_base/faq"
        VARCHAR category
        VARCHAR title
        TEXT content
        TEXT input_example
        TEXT output_example
        JSON tags
        INTEGER priority
        BOOLEAN is_active
    }
    
    agent_knowledge_base {
        VARCHAR knowledge_id PK "ID knowledge"
        VARCHAR agent_id FK "ID agent (NULL for general)"
        VARCHAR title
        TEXT content
        VARCHAR source
        VARCHAR category
        JSON tags
        JSON embedding_vector "For RAG"
        INTEGER access_count
        TIMESTAMP last_accessed_at
        BOOLEAN is_active
        BOOLEAN is_verified
    }
    
    %% ============================================
    %% ORGANIZATION AND DEPLOYMENT
    %% ============================================
    
    organizational_structure {
        VARCHAR id PK "ID Records"
        VARCHAR department "Division"
        VARCHAR division "Unit"
        VARCHAR position "Post"
        VARCHAR full_name "FIO"
        INTEGER hierarchy_level "Level of hierarchy"
        VARCHAR manager_id FK "ID Manager"
        VARCHAR agent_id FK "ID agent"
        ENUM employment_type "full_time/ai_agent"
        BOOLEAN is_active
    }
    
    deployed_agents_registry {
        VARCHAR deployment_id PK "ID deployment"
        VARCHAR agent_id FK "ID agent"
        VARCHAR telegram_bot_token
        VARCHAR telegram_username UK
        VARCHAR teams_app_id
        VARCHAR teams_bot_id
        JSON channel_roles
        ENUM deployment_status "deployed/stopped/maintenance"
        TIMESTAMP last_health_check
        JSON limits
        JSON performance_metrics
        TIMESTAMP last_activity
    }
    
    %% ============================================
    %% METRICS
    %% ============================================
    
    agent_performance_metrics {
        VARCHAR metric_id PK "ID metrics"
        VARCHAR agent_id FK "ID agent"
        VARCHAR metric_name "The name of the metrics"
        ENUM metric_type "counter/gauge/histogram"
        DECIMAL metric_value "Value"
        ENUM period "minute/hour/day/week/month"
        TIMESTAMP period_start
        TIMESTAMP period_end
        JSON dimensions
        TIMESTAMP recorded_at
    }
    
    system_metrics {
        VARCHAR id PK "ID metrics"
        VARCHAR metric_name
        DECIMAL metric_value
        VARCHAR agent_id FK "ID agent (optional)"
        VARCHAR period
        JSON metadata
        TIMESTAMP timestamp
    }
    
    %% ============================================
    %% LINKS BETWEEN TABLES
    %% ============================================
    
    %% Agents -> Prompts
    agents ||--o{ agent_prompts : "has prompts"
    
    %% Agents -> GPT Settings
    agents ||--|| agent_gpt_settings : "has settings"
    
    %% Agents -> Tools (Through mapping)
    agents ||--o{ agent_tools_mapping : "uses"
    agent_tools ||--o{ agent_tools_mapping : "available for"
    
    %% Agents -> Memory
    agents ||--o{ core_memory : "has core memory"
    agents ||--o{ operational_memory : "has operational memory"
    agents ||--o{ long_term_memory : "has long-term memory"
    
    %% Agents -> History and logs
    agents ||--o{ chat_history : "has history"
    agents ||--o{ agent_activity_log : "has logs"
    agents ||--o{ agent_version_history : "has versions"
    
    %% Agents -> Rules
    agents ||--o{ agent_rules : "has rules"
    agents ||--o{ agent_routing_rules : "routed from"
    agents ||--o{ agent_routing_rules : "routed to"
    
    %% Agents -> Training data
    agents ||--o{ agent_training_data : "has training data"
    agents ||--o{ agent_knowledge_base : "has a knowledge base"
    
    %% Agents -> Organization
    agents ||--o| organizational_structure : "submitted in accordance with"
    agents ||--o| deployed_agents_registry : "deployed as"
    
    %% Agents -> Meterics
    agents ||--o{ agent_performance_metrics : "has metrics"
    agents ||--o{ system_metrics : "related to"
    
    %% Organization -> Youre your own man (hierarchy)
    organizational_structure ||--o{ organizational_structure : "Obedience"
```

---

## 🎯 Architecture by group of tables

### 1. Agent Core Core)

```mermaid
graph TB
    subgraph "Agent Core"
        A[agents<br/>Basic information]
        P[agent_prompts<br/>System prompts]
        G[agent_gpt_settings<br/>GPT Settings]
        T[agent_tools_mapping<br/>Tools]
        
        A --> P
        A --> G
        A --> T
    end
    
    subgraph "Tools Catalog"
        TC[agent_tools<br/>Catalogue of tools]
        TC --> T
    end
    
    style A fill:#4CAF50,color:#fff
    style P fill:#2196F3,color:#fff
    style G fill:#2196F3,color:#fff
    style T fill:#2196F3,color:#fff
    style TC fill:#FF9800,color:#fff
```

### 2. Memory of the Agent (Memory of the Agent))

```mermaid
graph LR
    subgraph "Agent Memory System"
        A[agents]
        CM[core_memory<br/>Permanent memory<br/>Rules, facts]
        OM[operational_memory<br/>Operational memory<br/>Sessions, TTL]
        LTM[long_term_memory<br/>Long-term memory<br/>Training, Pathers]
        
        A --> CM
        A --> OM
        A --> LTM
    end
    
    style A fill:#4CAF50,color:#fff
    style CM fill:#E91E63,color:#fff
    style OM fill:#9C27B0,color:#fff
    style LTM fill:#673AB7,color:#fff
```

### 3. History and Logging)

```mermaid
graph TB
    subgraph "Logging System"
        A[agents]
        CH[chat_history<br/>History of communications<br/>Dialogues]
        AL[agent_activity_log<br/>Activity log<br/>Tool calls, errors]
        VH[agent_version_history<br/>Version History<br/>Change configuration]
        
        A --> CH
        A --> AL
        A --> VH
    end
    
    style A fill:#4CAF50,color:#fff
    style CH fill:#00BCD4,color:#fff
    style AL fill:#00BCD4,color:#fff
    style VH fill:#00BCD4,color:#fff
```

### 4. Rules and router (Rules & Routing))

```mermaid
graph TB
    subgraph "Rules & Routing"
        A1[agents]
        A2[agents]
        A3[agents]
        
        R[agent_rules<br/>Rules of conduct]
        RR[agent_routing_rules<br/>Routeing rules]
        
        A1 --> R
        A1 -->|source| RR
        A2 -->|target| RR
        A3 -->|target| RR
    end
    
    style A1 fill:#4CAF50,color:#fff
    style A2 fill:#4CAF50,color:#fff
    style A3 fill:#4CAF50,color:#fff
    style R fill:#FF5722,color:#fff
    style RR fill:#FF5722,color:#fff
```

### 5. Training & Knowledge)

```mermaid
graph TB
    subgraph "Training & Knowledge"
        A[agents]
        TD[agent_training_data<br/>Few-Shot Examples<br/>Scenarios, briefcases]
        KB[agent_knowledge_base<br/>Knowledge base RAG<br/>Vector Search]
        
        A --> TD
        A --> KB
    end
    
    style A fill:#4CAF50,color:#fff
    style TD fill:#FFC107,color:#000
    style KB fill:#FFC107,color:#000
```

### 6. Deployment and metrics (Deployment & Metrics))

```mermaid
graph TB
    subgraph "Deployment & Metrics"
        A[agents]
        OS[organizational_structure<br/>Organization<br/>Hierarchy]
        DR[deployed_agents_registry<br/>Deployment roster<br/>Tokens, Status]
        PM[agent_performance_metrics<br/>Productivity metrics]
        SM[system_metrics<br/>System metrics]
        
        A --> OS
        A --> DR
        A --> PM
        A --> SM
    end
    
    style A fill:#4CAF50,color:#fff
    style OS fill:#795548,color:#fff
    style DR fill:#795548,color:#fff
    style PM fill:#607D8B,color:#fff
    style SM fill:#607D8B,color:#fff
```

---

## 🔄 Agent's Life Cycle

```mermaid
flowchart TD
    Start([Creation of an agent]) --> Create[Box in agents]
    
    Create --> Config{Settings}
    Config --> Prompt[Add Pumpt<br/>agent_prompts]
    Config --> GPT[Settings GPT<br/>agent_gpt_settings]
    Config --> Tools[Communication with tools<br/>agent_tools_mapping]
    Config --> Memory[Initiating memory<br/>core_memory]
    
    Prompt --> Rules[Addendum of Regulations<br/>agent_rules]
    GPT --> Rules
    Tools --> Rules
    Memory --> Rules
    
    Rules --> Routes[Routeing settings<br/>agent_routing_rules]
    
    Routes --> Deploy[Deployment<br/>deployed_agents_registry]
    
    Deploy --> Active{Agent &apos; s work}
    
    Active --> Chat[Processing of communications<br/>chat_history]
    Active --> Activity[Logging activity<br/>agent_activity_log]
    Active --> OpMem[Operational memory<br/>operational_memory]
    Active --> Metrics[Collection of metrics<br/>agent_performance_metrics]
    
    Chat --> Learn[Training<br/>long_term_memory]
    
    Active --> Update{Update?}
    Update -->|Yes.| Version[New version<br/>agent_version_history]
    Version --> Config
    Update -->|None| Active
    
    Active --> Archive{Archiving?}
    Archive -->|Yes.| End([Status: archived])
    Archive -->|None| Active
    
    style Start fill:#4CAF50,color:#fff
    style Create fill:#2196F3,color:#fff
    style Active fill:#FF9800,color:#fff
    style End fill:#F44336,color:#fff
```

---

## 🌊 Data flow during request processing

```mermaid
sequenceDiagram
    participant U as User
    participant A as agents
    participant P as agent_prompts
    participant G as agent_gpt_settings
    participant T as agent_tools
    participant CM as core_memory
    participant OM as operational_memory
    participant CH as chat_history
    participant AL as agent_activity_log
    participant PM as agent_performance_metrics
    
    U->>A: User Request
    A->>P: Loading Prompt
    A->>G: Loading GPT settings
    A->>CM: Loading core Memory
    A->>OM: Loading the context of the session
    
    Note over A,G: Formation of a request to GPT
    
    A->>T: Checking available tools
    
    Note over A,T: Challenge GPT with prompt,<br/>memory and tools
    
    T-->>A: Result tool calls
    A->>AL: Logging tool calls
    
    A->>CH: Saving communication
    A->>OM: Updating the context
    A->>PM: Recording of metrics
    
    A-->>U: Response to User
```

---

## 📦 Grouping of tables by purpose

```mermaid
mindmap
  root((Workflow Office<br/>Database))
    Agent Core
      agents
      agent_prompts
      agent_gpt_settings
      agent_tools
      agent_tools_mapping
    Memory
      core_memory
      operational_memory
      long_term_memory
    Logging
      chat_history
      agent_activity_log
      agent_version_history
    Rules
      agent_rules
      agent_routing_rules
    Training
      agent_training_data
      agent_knowledge_base
    Deployment
      organizational_structure
      deployed_agents_registry
    Metrics
      agent_performance_metrics
      system_metrics
```

---

## 🔗 Agents &apos; links (tracking))

```mermaid
graph TD
    subgraph "HR Team Routing"
        S[Supervisor<br/>@boss.ai]
        R[Recruiter<br/>@alena.ai]
        SC[Scrinner<br/>@sergei.ai]
        
        S -->|delegation:<br/>Search for candidates| R
        S -->|delegation:<br/>screening| SC
        R -->|delegation:<br/>Detailed screening| SC
        R -->|report:<br/>Candidates found| S
        SC -->|report:<br/>Results of screening| R
        SC -->|report:<br/>Final reports| S
    end
    
    style S fill:#4CAF50,color:#fff
    style R fill:#2196F3,color:#fff
    style SC fill:#FF9800,color:#fff
```

---

## 📊 Table statistics

| Category | Tables | Main function |
|-----------|--------|---------------------|
| **Agent Core** | 5 | Basic information, prompts, settings, tools |
| **Memory** | 3 | Core, Operational, Long-term memory |
| **Logging** | 3 | chat history, activity logs, versions |
| **Rules** | 2 | Rules of conduct and routeting |
| **Training** | 2 | Training data and knowledge base |
| **Deployment** | 2 | Structure and deployment roster |
| **Metrics** | 2 | Productivity metrics and systems |
| **TOTAL** | **19** | Full agent ecosystem |

---

## 🎨 Color legend

- 🟢 **Green** - Basic Agent Tables (agents))
- 🔵 **Blue** - configuration (prompts, settings, tools))
- 🟣 **Core, operational, long-term memory)
- 🔷 **Blue** - Logging (history, logs, versions))
- 🔴 **Red** - Rules)
- 🟡 **Yellow** - Training (training, knowledge))
- 🟤 **Brown** - Deployment (org, registration))
- ⚫ **Grey**-Metrics (performance, system))

---

## 🚀 Benefits of architecture

### ✅ Normalization
- No duplication of data
- Easily updated components
- Integrity through external keys

### ✅ Scale
- Independent storage of components
- Horizontal scale
- Optimized indices

### ✅ Flexible
- JSON Castomization Fields
- Modular architecture
- The configuration version

### ✅ Productivity
- Indexes on all FK and frequently used fields
- Submissions (views) for frequent queries
- TTL for auto-cleaning of temporary data

---

**Audience:** Workflow Office Team  
** Version:** 2.0.0  
**Date:** 2025-10-13

