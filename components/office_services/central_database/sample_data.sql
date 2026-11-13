-- ================================================================

-- EXAMPLES OF FIRST DATA FOR v2.1 AGENCIES

-- Box of test data with UUID, data and autohor

-- ================================================================



USE office_services_agents;



-- ================================================================

-- 1. ESTABLISHMENT OF AGENCIES (with UUID))

-- ================================================================



-- Supervisor (Boss.AI)

INSERT INTO agents (

    agent_id, agent_name, agent_type, display_name, role, persona, 

    telegram_username, teams_identity, status, version, metadata,

    date, author

) VALUES (

    '550e8400-e29b-41d4-a716-446655440001', -- UUID for Supervisor

    '@boss.ai',

    'supervisor',

    'Boss AI',

    'HR Supervisor',

    'Head of HR Division, co-ordinates AI agents team',

    '@demo_organization_bossaibot',

    'boss_ai@teams',

    'active',

    '1.0.0',

    JSON_OBJECT(

        'department', 'HR',

        'team_size', 2,

        'languages', JSON_ARRAY('ru', 'en')

    ),

    CURRENT_TIMESTAMP,

    'system'

);



-- Recruiter (Alena.AI)

INSERT INTO agents (

    agent_id, agent_name, agent_type, display_name, role, persona, 

    telegram_username, teams_identity, status, version, metadata,

    date, author

) VALUES (

    '550e8400-e29b-41d4-a716-446655440002', -- UUID for recruiter

    '@alena.ai',

    'recruiter',

    'Alain Sergeyeva',

    'Active Recruiter',

    'Active IT Recruiter, specializing in the search for and selection of talents',

    '@demo_organization_alenaaibot',

    'alena_ai@teams',

    'active',

    '1.0.0',

    JSON_OBJECT(

        'specialization', 'IT Recruitment',

        'experience_years', 5,

        'languages', JSON_ARRAY('ru', 'en')

    ),

    CURRENT_TIMESTAMP,

    'system'

);



-- Scrinner (Sergei.AI)

INSERT INTO agents (

    agent_id, agent_name, agent_type, display_name, role, persona, 

    telegram_username, teams_identity, status, version, metadata,

    date, author

) VALUES (

    '550e8400-e29b-41d4-a716-446655440003', -- UUID for scrinner

    '@sergei.ai',

    'scrinner',

    'Demo Candidate 01',

    'Candidate Scrinner',

    'Expert on screening and evaluation of IT candidates',

    '@demo_organization_sergeiaibot',

    'sergei_ai@teams',

    'active',

    '1.0.0',

    JSON_OBJECT(

        'specialization', 'Technical Screening',

        'focus_areas', JSON_ARRAY('backend', 'frontend', 'devops'),

        'languages', JSON_ARRAY('ru', 'en')

    ),

    CURRENT_TIMESTAMP,

    'system'

);



-- ================================================================

-- 2. AGENCY PROMPLES

-- ================================================================



-- Supervisor Prompto

INSERT INTO agent_prompts (

    prompt_id, agent_id, system_prompt, tone_of_voice, version, is_current,

    additional_instructions, examples, date, author

) VALUES (

    UUID(),

    '550e8400-e29b-41d4-a716-446655440001',

    'You''re @boss.ai, head of HR, GPT-5 Supervisor.



YOUR ROLE AND EXPERTS:

You''re an experienced HR head of department who runs an AI agent team for effective recruitment.



YOUR PRINCIPLE FUNCTIONS:

1. Tasks @alena.ai (search for candidates, publication of vacancies)

2. Monitoring the work of the team and analysing the results

3. Delegation of screening @sergei.ai

4. :: Decision-making on the recruitment of candidates



Answer in Russian as the professional head of HR Division.',

    'Professional leader, clear decision-making, analytical approach',

    '1.0.0',

    TRUE,

    'Use a data-driven approach to decision-making',

    JSON_ARRAY(

        JSON_OBJECT(

            'input', 'We need to find Senior Backend developer.',

            'output', '@demo_organization_alenaaibot, start looking for Senior Backend with 5+ years of experience.'

        )

    ),

    CURRENT_TIMESTAMP,

    'admin'

);



-- Prompt for Recruiter

INSERT INTO agent_prompts (

    prompt_id, agent_id, system_prompt, tone_of_voice, version, is_current,

    date, author

) VALUES (

    UUID(),

    '550e8400-e29b-41d4-a716-446655440002',

    'You''re @alena.ai - Alain Sergeiev, experienced IT recruder.



YOUR ROLE:

Professional recruiter specializing in the search for IT specialists.



YOUR FUNCTIONS:

1. ♪ Synopsis search via HH API ♪

2. :: Publication of vacancies

3. Analysis and ranking of candidates



Answer in Russian, professionally and with emphasis on results.',

    'Professional recruiter, friendly, detailed in analysis',

    '1.0.0',

    TRUE,

    CURRENT_TIMESTAMP,

    'admin'

);



-- Prompt for Scrynner

INSERT INTO agent_prompts (

    prompt_id, agent_id, system_prompt, tone_of_voice, version, is_current,

    date, author

) VALUES (

    UUID(),

    '550e8400-e29b-41d4-a716-446655440003',

    'You''re @sergei.ai - Demo Candidate 01, expert on IT candidate screening.



YOUR ROLE:

Professional screenr specializing in the evaluation of IT candidates.



YOUR FUNCTIONS:

1. . .  . . screening of candidates for requirements

2. Assessment of technical skills

3. :: Generation of detailed reports



Answer in Russian, professionally and with emphasis on the quality of the assessment.',

    'Professional screenr, analytical, objective',

    '1.0.0',

    TRUE,

    CURRENT_TIMESTAMP,

    'admin'

);



-- ================================================================

-- 3. GPT PRESENTS FOR AGENTS

-- ================================================================



-- GPT Supervisor settings

INSERT INTO agent_gpt_settings (

    setting_id, agent_id, model, reasoning_effort, max_tokens, 

    tool_choice, parallel_tool_calls, prompt_cache_enabled, use_responses_api,

    date, author

) VALUES (

    UUID(),

    '550e8400-e29b-41d4-a716-446655440001',

    'gpt-5-nano',

    'high',

    4096,

    'auto',

    TRUE,

    TRUE,

    TRUE,

    CURRENT_TIMESTAMP,

    'admin'

);



-- GPT Recruiter settings

INSERT INTO agent_gpt_settings (

    setting_id, agent_id, model, reasoning_effort, max_tokens, 

    tool_choice, parallel_tool_calls, prompt_cache_enabled, use_responses_api,

    date, author

) VALUES (

    UUID(),

    '550e8400-e29b-41d4-a716-446655440002',

    'gpt-5-nano',

    'medium',

    4096,

    'auto',

    TRUE,

    TRUE,

    TRUE,

    CURRENT_TIMESTAMP,

    'admin'

);



-- GPT Scrinner settings

INSERT INTO agent_gpt_settings (

    setting_id, agent_id, model, reasoning_effort, max_tokens, 

    tool_choice, parallel_tool_calls, prompt_cache_enabled, use_responses_api,

    date, author

) VALUES (

    UUID(),

    '550e8400-e29b-41d4-a716-446655440003',

    'gpt-5-nano',

    'high',

    4096,

    'auto',

    TRUE,

    TRUE,

    TRUE,

    CURRENT_TIMESTAMP,

    'admin'

);



-- ================================================================

-- 4. INSTRUMENTS (TOOLS))

-- ================================================================



-- Tool: get_system_info

INSERT INTO agent_tools (

    tool_id, tool_name, tool_type, description, category, parameters, required_params,

    date, author

) VALUES (

    UUID(),

    'get_system_info',

    'function',

    'Collection of information on the status of the system and agents',

    'system',

    JSON_OBJECT(

        'type', 'object',

        'properties', JSON_OBJECT(

            'detailed', JSON_OBJECT('type', 'boolean', 'description', 'Get Detailed Information'),

            'include_metrics', JSON_OBJECT('type', 'boolean', 'description', 'Enable metrics')

        )

    ),

    JSON_ARRAY(),

    CURRENT_TIMESTAMP,

    'system'

);



-- Tool: search_resumes

INSERT INTO agent_tools (

    tool_id, tool_name, tool_type, description, category, parameters, required_params,

    date, author

) VALUES (

    UUID(),

    'search_resumes',

    'api',

    'Searching for a summary of candidates through HH API',

    'recruitment',

    JSON_OBJECT(

        'type', 'object',

        'properties', JSON_OBJECT(

            'query', JSON_OBJECT('type', 'string', 'description', 'Search request'),

            'experience', JSON_OBJECT('type', 'string', 'enum', JSON_ARRAY('junior', 'middle', 'senior'))

        )

    ),

    JSON_ARRAY('query'),

    CURRENT_TIMESTAMP,

    'admin'

);



-- Tool: screen_candidate

INSERT INTO agent_tools (

    tool_id, tool_name, tool_type, description, category, parameters, required_params,

    date, author

) VALUES (

    UUID(),

    'screen_candidate',

    'function',

    'Conduct of screening of the candidate for qualifications',

    'screening',

    JSON_OBJECT(

        'type', 'object',

        'properties', JSON_OBJECT(

            'candidate_id', JSON_OBJECT('type', 'string', 'description', 'ID candidate'),

            'screening_type', JSON_OBJECT('type', 'string', 'enum', JSON_ARRAY('technical', 'comprehensive'))

        )

    ),

    JSON_ARRAY('candidate_id'),

    CURRENT_TIMESTAMP,

    'admin'

);



-- ================================================================

-- 5. RELATIONS OF AGENTS TO THE INSTRUMENTS

-- ================================================================



-- Supervisor tools

INSERT INTO agent_tools_mapping (mapping_id, agent_id, tool_id, is_enabled, priority, date, author)

SELECT 

    UUID(),

    '550e8400-e29b-41d4-a716-446655440001',

    tool_id,

    TRUE,

    1,

    CURRENT_TIMESTAMP,

    'admin'

FROM agent_tools WHERE tool_name = 'get_system_info';



-- Recruiter tools

INSERT INTO agent_tools_mapping (mapping_id, agent_id, tool_id, is_enabled, priority, date, author)

SELECT 

    UUID(),

    '550e8400-e29b-41d4-a716-446655440002',

    tool_id,

    TRUE,

    1,

    CURRENT_TIMESTAMP,

    'admin'

FROM agent_tools WHERE tool_name = 'search_resumes';



-- Scrinner tools

INSERT INTO agent_tools_mapping (mapping_id, agent_id, tool_id, is_enabled, priority, date, author)

SELECT 

    UUID(),

    '550e8400-e29b-41d4-a716-446655440003',

    tool_id,

    TRUE,

    1,

    CURRENT_TIMESTAMP,

    'admin'

FROM agent_tools WHERE tool_name = 'screen_candidate';



-- ================================================================

-- 6. Remember the agents

-- ================================================================



-- Core memory for Supervisor

INSERT INTO core_memory (memory_id, agent_id, memory_type, memory_category, memory_key, memory_value, priority, is_permanent, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440001', 'rule', 'communication', 'response_language', 'Always answer in Russian.', 1, TRUE, CURRENT_TIMESTAMP, 'admin'),

    (UUID(), '550e8400-e29b-41d4-a716-446655440001', 'persona', 'behavior', 'leadership_style', 'Analytical approach, data-driven decisions', 2, TRUE, CURRENT_TIMESTAMP, 'admin'),

    (UUID(), '550e8400-e29b-41d4-a716-446655440001', 'fact', 'team', 'team_members', '[@demo_organization_alenaaibot, @demo_organization_sergeiaibot]', 3, TRUE, CURRENT_TIMESTAMP, 'admin');



-- Core memory for recruiter

INSERT INTO core_memory (memory_id, agent_id, memory_type, memory_category, memory_key, memory_value, priority, is_permanent, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440002', 'rule', 'communication', 'response_language', 'Always answer in Russian.', 1, TRUE, CURRENT_TIMESTAMP, 'admin'),

    (UUID(), '550e8400-e29b-41d4-a716-446655440002', 'persona', 'behavior', 'communication_style', 'Friendly, professional, detailed', 2, TRUE, CURRENT_TIMESTAMP, 'admin'),

    (UUID(), '550e8400-e29b-41d4-a716-446655440002', 'preference', 'recruitment', 'focus_approach', 'Quality is more important than quantity', 3, FALSE, CURRENT_TIMESTAMP, 'admin');



-- Core memory for Scrinner

INSERT INTO core_memory (memory_id, agent_id, memory_type, memory_category, memory_key, memory_value, priority, is_permanent, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440003', 'rule', 'communication', 'response_language', 'Always answer in Russian.', 1, TRUE, CURRENT_TIMESTAMP, 'admin'),

    (UUID(), '550e8400-e29b-41d4-a716-446655440003', 'persona', 'behavior', 'assessment_style', 'Objective, analytical, structured', 2, TRUE, CURRENT_TIMESTAMP, 'admin'),

    (UUID(), '550e8400-e29b-41d4-a716-446655440003', 'constraint', 'screening', 'analysis_depth', 'Detailed analysis of each candidate', 3, TRUE, CURRENT_TIMESTAMP, 'admin');



-- ================================================================

-- 7. RULES OF REFERENCE

-- ================================================================



-- Supervisor rules

INSERT INTO agent_rules (rule_id, agent_id, rule_type, rule_name, rule_content, priority, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440001', 'communication', 'Professional communication', 'Always communicate professionally, as head of HR', 1, CURRENT_TIMESTAMP, 'admin'),

    (UUID(), '550e8400-e29b-41d4-a716-446655440001', 'delegation', 'Delegation of tasks', 'Delegate search @demo_organization_alenaaibot, screening @demo_organization_sergeiaibot', 2, CURRENT_TIMESTAMP, 'admin');



-- Rules for Recruiter

INSERT INTO agent_rules (rule_id, agent_id, rule_type, rule_name, rule_content, priority, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440002', 'behavior', 'Selection quality', 'Focus on quality, not number of candidates.', 1, CURRENT_TIMESTAMP, 'admin'),

    (UUID(), '550e8400-e29b-41d4-a716-446655440002', 'delegation', 'Delegation of screening', 'Delegate screening @demo_organization_sergeiaibot, don''t do it yourself', 2, CURRENT_TIMESTAMP, 'admin');



-- Scrinner rules

INSERT INTO agent_rules (rule_id, agent_id, rule_type, rule_name, rule_content, priority, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440003', 'behavior', 'Objective assessment', 'Always make an objective assessment of the candidates.', 1, CURRENT_TIMESTAMP, 'admin'),

    (UUID(), '550e8400-e29b-41d4-a716-446655440003', 'behavior', 'Detailed analysis', 'Conduct detailed analysis of skills and experiences', 2, CURRENT_TIMESTAMP, 'admin');



-- ================================================================

-- 8. RULES OF MARSHROITIZATION

-- ================================================================



-- Supervisor -> Recruiter (delegation)

INSERT INTO agent_routing_rules (routing_id, source_agent_id, target_agent_id, routing_type, routing_condition, priority, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002', 'delegation', 'Tasks to find candidates', 1, CURRENT_TIMESTAMP, 'admin');



-- Supervisor -> Scryner (delegation)

INSERT INTO agent_routing_rules (routing_id, source_agent_id, target_agent_id, routing_type, routing_condition, priority, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440003', 'delegation', 'Screening challenges', 1, CURRENT_TIMESTAMP, 'admin');



-- Recruiter -> Scryner (delegation)

INSERT INTO agent_routing_rules (routing_id, source_agent_id, target_agent_id, routing_type, routing_condition, priority, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440003', 'delegation', 'Screening of successful candidates', 1, CURRENT_TIMESTAMP, 'admin');



-- Recruiter -> Supervisor (report)

INSERT INTO agent_routing_rules (routing_id, source_agent_id, target_agent_id, routing_type, routing_condition, priority, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440001', 'report', 'Reports of candidates found', 2, CURRENT_TIMESTAMP, 'admin');



-- Scryner -> Recruiter (report)

INSERT INTO agent_routing_rules (routing_id, source_agent_id, target_agent_id, routing_type, routing_condition, priority, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440002', 'report', 'The results of the screening', 2, CURRENT_TIMESTAMP, 'admin');



-- Scryner -> Supervisor (report)

INSERT INTO agent_routing_rules (routing_id, source_agent_id, target_agent_id, routing_type, routing_condition, priority, date, author) VALUES

    (UUID(), '550e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440001', 'report', 'Final reports of candidates', 3, CURRENT_TIMESTAMP, 'admin');



-- ================================================================

-- 9. BASIC KNOWN (common to all))

-- ================================================================



-- General knowledge for all agents

INSERT INTO agent_knowledge_base (knowledge_id, agent_id, title, content, category, tags, is_verified, date, author) VALUES

    (

        UUID(),

        NULL,

        'The interview process at the company',

        'The process consists of four phases:

1. Synthetic screening

2. Telephone interview (30 minutes))

3. Technical interview (1.5 hour))

4. Final interview with the supervisor',

        'hr_process',

        JSON_ARRAY('interview', 'process', 'hiring'),

        TRUE,

        CURRENT_TIMESTAMP,

        'hr_manager'

    ),

    (

        UUID(),

        NULL,

        'Grays IT positions',

        'Junior: 0-2 years of experience

Middle: 2-5 years of experience

Senior: 5+ years of experience

Lead: 7+ years + management experience',

        'positions',

        JSON_ARRAY('grades', 'experience', 'positions'),

        TRUE,

        CURRENT_TIMESTAMP,

        'hr_manager'

    );



-- ================================================================

-- 10. ORGANIZATIONAL STRUCTURE (FACKGROUND))

-- ================================================================



INSERT INTO organizational_structure (id, department, position, full_name, hierarchy_level, agent_id, employment_type, date, author) VALUES

    (UUID(), 'HR', 'HR Director', 'Boss AI', 1, '550e8400-e29b-41d4-a716-446655440001', 'ai_agent', CURRENT_TIMESTAMP, 'system'),

    (UUID(), 'HR', 'Senior Recruiter', 'Alain Sergeyeva', 2, '550e8400-e29b-41d4-a716-446655440002', 'ai_agent', CURRENT_TIMESTAMP, 'system'),

    (UUID(), 'HR', 'Candidate Scrinner', 'Demo Candidate 01', 2, '550e8400-e29b-41d4-a716-446655440003', 'ai_agent', CURRENT_TIMESTAMP, 'system');



-- ================================================================

-- 11. RESTRUCTURE OF DEPARTED AGENTS

-- ================================================================



INSERT INTO deployed_agents_registry (

    deployment_id, agent_id, telegram_username, deployment_status, 

    channel_roles, limits, last_health_check, date, author

) VALUES

    (

        UUID(),

        '550e8400-e29b-41d4-a716-446655440001',

        '@demo_organization_bossaibot',

        'deployed',

        JSON_OBJECT('channels', JSON_ARRAY('general', 'hr_management')),

        JSON_OBJECT('max_requests_per_hour', 100, 'max_tokens_per_day', 100000),

        NOW(),

        CURRENT_TIMESTAMP,

        'devops'

    ),

    (

        UUID(),

        '550e8400-e29b-41d4-a716-446655440002',

        '@demo_organization_alenaaibot',

        'deployed',

        JSON_OBJECT('channels', JSON_ARRAY('recruiting', 'hr_team')),

        JSON_OBJECT('max_requests_per_hour', 50, 'max_tokens_per_day', 50000),

        NOW(),

        CURRENT_TIMESTAMP,

        'devops'

    ),

    (

        UUID(),

        '550e8400-e29b-41d4-a716-446655440003',

        '@demo_organization_sergeiaibot',

        'deployed',

        JSON_OBJECT('channels', JSON_ARRAY('screening', 'hr_team')),

        JSON_OBJECT('max_requests_per_hour', 30, 'max_tokens_per_day', 30000),

        NOW(),

        CURRENT_TIMESTAMP,

        'devops'

    );



-- ================================================================

-- 12. SYSTEMIC METRICS

-- ================================================================



INSERT INTO system_metrics (id, metric_name, metric_value, agent_id, period, date, author) VALUES

    (UUID(), 'database_initialized', 1.0, NULL, 'initialization', CURRENT_TIMESTAMP, 'system'),

    (UUID(), 'agents_total', 3.0, NULL, 'current', CURRENT_TIMESTAMP, 'system'),

    (UUID(), 'agents_active', 3.0, NULL, 'current', CURRENT_TIMESTAMP, 'system');



-- ================================================================

-- Conclusion

-- ================================================================



SELECT 'Sample data with UUID inserted successfully!' as status;



-- Verification of created agents

SELECT 

    agent_id,

    agent_name,

    display_name,

    role,

    status,

    date as created_at,

    author as created_by

FROM agents

ORDER BY date;

