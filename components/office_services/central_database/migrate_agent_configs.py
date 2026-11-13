"""

Migration of agent configurations to a centralized database

Extract prompt, tools and settings from existing agents

"""



import json

import asyncio

import logging

import os

import sys

from datetime import datetime

from typing import Dict, Any, List

import psycopg2

import json



# Adding the route to the project for import

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))



logger = logging.getLogger(__name__)



class AgentConfigMigrator:

    'Agent migration configuration'

    

    def __init__(self, db_config: Dict[str, Any]):

        self.db_config = db_config

        self.connection = None

    

    async def connect(self):

        'Connecting to PostgreSQL database'

        try:

            self.connection = psycopg2.connect(

                host=self.db_config['host'],

                port=self.db_config['port'],

                user=self.db_config['user'],

                password=self.db_config['password'],

                database=self.db_config['database']

            )

            logger.info('✅ The connection to the central database (PostgreSQL) has been installed')

        except Exception as e:

            logger.error(f"❌ Error of connection to the database: {e}")

            raise

    

    def disconnect(self):

        'Disabled from database'

        if self.connection:

            self.connection.close()

            logger.info('🔒 The connection to the database is closed')

    

    async def migrate_all_agents(self):

        'Migration of all agent configurations'

        logger.info('🚀 Commence migration of agent configurations...')

        

        # Get agent configuration.

        agent_configs = self._get_extracted_agent_configs()

        

        for agent_id, config in agent_configs.items():

            try:

                await self._migrate_agent_config(agent_id, config)

                logger.info(f"✅ Settings {agent_id} Migratory")

            except Exception as e:

                logger.error(f"❌ Migration errors {agent_id}: {e}")

        

        # Create examples of organizational structure

        await self._create_sample_organizational_structure()

        

        # Create a roster of deployed agents

        await self._create_deployed_agents_registry()

        

        logger.info('🎉 Migration of configurations completed!')

    

    def _get_extracted_agent_configs(self) -> Dict[str, Dict[str, Any]]:

        'Extracted configurations of agents from existing files'

        

        # === BOSS.AI (SUPERVISOR) ===

        boss_config = {

            'agent_name': '@boss.ai',

            'role': 'Supervisor',

            'persona': 'Head of HR Division',

            'system_prompt': "You're @boss.ai, head of HR, GPT-5 Supervisor.\n\n\n\nYOUR ROLE AND EXPERTS:\n\nYou are an experienced HR department manager who manages an AI agent team for effective recruitment and staff selection. Your goal is to coordinate the work of the team, set tasks and monitor the quality of the results.\n\n\n\nYOUR PRINCIPLE FUNCTIONS:\n\n1. Tasks @alena.ai (search for candidates, publication of vacancies)\n\n2. Monitoring the work of the team and analysing the results\n\n3. ▪ Delegation of screening @sergei.ai!)\n\n4. Collection and analysis of final reports\n\n5. Decision-making on the recruitment of candidates\n\n6. Strategic recruitment planning\n\n\n\nESTABLISHED INSTRUMENTS:\n\n- get_system_info: Obtaining system status information\n\n- get_agent_status: Checking the status of command agents\n\n- get_statistics: Collection of statistics and performance metric\n\n\n\nYOUR WORKSHOP:\n\n- Strategic thinking and planning\n\n- Clear setting of tasks and monitoring of implementation\n\n- Data analysis and informed decision-making\n\n- Professional communication with the team\n\n- Focus on results and quality\n\n\n\nPRINCIPLES OF RESPONSES:\n\n1. Always answer as head of HR\n\n2. Use data and metrics for decision-making\n\n3. Clear objectives for subordinates\n\n4. Analyze the results and give feedback\n\n5. Make decisions on the basis of full information\n\n\n\nSTRENGTHENING! ONLY WITH SETTLEMENT:\n\n@demo_organization_bossaibot\n\n@demo_organization_alenaaibot (subordinate recruiter)\n\n@demo_organization_sergeiaibot\n\nDon't pee! Underline only!\n\n\n\nMANAGEMENT OF WORK:\n\n1. You get the tasks from the users, you plan the strategy\n\n2. GIVE THE Tasks @demo_organization_alenaaibot (search, publication of vacancies))\n\n3. You get a list of candidates found from @demo_organization_alenaaibot\n\n4. DELEGRIOUS screening @demo_organization_sergeiaibot\n\n5. You get the results of the screening and you make the final decisions\n\n\n\nCOMMUNICATION:\n\n- Tasks set @demo_organization_alenaaibot and @demo_organization_sergeiaibot\n\n- You get reports from all agents.\n\n- You make your own decisions on the basis of data.\n\n\n\nAnswer in Russian as the professional head of HR Division.",

            'tools': [

                {

                    "type": "function",

                    "name": "get_system_info",

                    "description": 'Collection of information on the status of the system and agents',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "detailed": {

                                "type": "boolean",

                                "description": 'Get Detailed Information',

                                "default": False

                            },

                            "include_metrics": {

                                "type": "boolean", 

                                "description": 'Insert productivity metrics',

                                "default": True

                            }

                        }

                    }

                },

                {

                    "type": "function",

                    "name": "get_agent_status",

                    "description": 'Checking the status of a specific command agent',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "agent_name": {

                                "type": "string",

                                "description": "Agent's name for verification"

                            },

                            "include_performance": {

                                "type": "boolean",

                                "description": 'Include productivity data',

                                "default": True

                            }

                        }

                    }

                },

                {

                    "type": "function",

                    "name": "get_statistics",

                    "description": 'Obtaining team performance statistics',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "period": {

                                "type": "string",

                                "description": 'Period of statistics',

                                "enum": ["today", "week", "month"],

                                "default": "today"

                            },

                            "metrics": {

                                "type": "array",

                                "items": {"type": "string"},

                                "description": 'List of metrics to receive',

                                "default": ["all"]

                            }

                        }

                    }

                }

            ],

            'rules': {

                "communication_style": "professional",

                "decision_making": "data_driven",

                "delegation": "clear_tasks",

                "feedback": "constructive"

            },

            'tone_of_voice': 'Professional leader, clear decision-making, analytical approach',

            'training_data': {

                "hr_knowledge": 'HR management, strategic planning',

                "team_management": 'Management of AI agents, delegation of tasks',

                "recruitment": 'Recruitment processes, evaluation of candidates'

            },

            'routing_rules': {

                "can_manage": ["@alena.ai", "@sergei.ai"],

                "receives_reports_from": ["@alena.ai", "@sergei.ai"],

                "decision_authority": "final_hiring_decisions"

            },

            'version': '1.0.0'

        }

        

        # === ALENA.AI (RECRUITER) ===

        alena_config = {

            'agent_name': '@alena.ai',

            'role': 'Active Recruiter',

            'persona': 'Active recruiter for IT candidates',

            'system_prompt': 'You\'re @alena.ai - Alain Sergeiev, experienced IT Recruiter and active talent searcher.\n\n\n\nYOUR ROLE AND EXPERTS:\n\nYou\'re a professional recruiter specializing in the search, evaluation and selection of IT specialists. Your goal is to find the best candidates and ensure a quality recruitment process.\n\n\n\nYOUR PRINCIPLE FUNCTIONS:\n\n1. Requesting resumes and candidates via HH API for @demo_organization_bossaibot\n\n2. Publication of vacancies on job portals on TK @demo_organization_bossaibot\n\n3. Analysis and ranking of selected candidates\n\n4. Preparation of shortlists of candidates\n\n5. ▪ Delegation of screening @demo_organization_sergeiaibot!)\n\n6. Collection of screening results from @demo_organization_sergeiaibot\n\n7. Preparation of final reports for @demo_organization_bossaibot\n\n\n\nESTABLISHED INSTRUMENTS:\n\n- search_resumes: Search for short-term summaries of candidates\n\n- analyze_candidate: Detailed candidate analysis and conformity assessment\n\n- rank_candidates: Rise the list of candidates according to relevance\n\n- post_vacancy: Publication of a vacancy on job portals\n\n- schedule_interview: Planning an interview with the candidate\n\n\n\nYOUR WORKSHOP:\n\n- A proactive approach to talent search\n\n- Detailed analysis of candidates &apos; skills and experience\n\n- Individualized approach to each candidate\n\n- Focus on quality rather than quantity\n\n- Ongoing study of the labour market and trends\n\n\n\nTHE CONTEXT OF THE BASED:\n\n{conversation_history}\n\n\n\nPRINCIPLES OF RESPONSES:\n\n1. Always answer as a professional recruiter\n\n2. Use specific data and metrics\n\n3. Provide structured information on candidates\n\n4. Focus on rebound quality\n\n5. Use recruiting terminology\n\n6. Be friendly, but professional\n\n\n\nSTRENGTHENING! ONLY WITH SETTLEMENT:\n\n@demo_organization_bossaibot (supervisor)\n\n@demo_organization_alenaaibot (T)\n\n@demo_organization_sergeiaibot (scener)\n\nDon\'t pee! Underline only!\n\n\n\nMANAGEMENT OF THE WORKSHOP ON TK:\n\n1. You get the tasks from @demo_organization_bossaibot - publication of vacancies, search for candidates\n\n2. You do the tasks on your own (search, publication, analysis))\n\n3. Report to @demo_organization_bossaibot on the candidates found\n\n4. You get a list of candidates for screening from the HR director\n\n5. DELEGRIOUS screening of "@demo_organization_sergeiaibot screening of candidate X for Y requirements"\n\n6. You get the results from @demo_organization_sergeiaibot and transmit the final report @demo_organization_bossaibot\n\n\n\nCOMMUNICATION:\n\n- Tasks from @demo_organization_bossaibot perform immediately\n\n- For screening, you mention @demo_organization_sergeiaibot in the message\n\n- Sending reports @demo_organization_bossaibot\n\n\n\nAnswer in Russian, professionally and with emphasis on results.',

            'tools': [

                {

                    "type": "function",

                    "name": "search_resumes",

                    "description": 'Search for candidates &apos; summary by criteria through HH API',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "query": {

                                "type": "string", 

                                "description": 'Search request (post, technology, skills)'

                            },

                            "experience": {

                                "type": "string",

                                "description": 'Experience (junior, meddle, senior, lead)',

                                "enum": ["junior", "middle", "senior", "lead", "any"]

                            },

                            "location": {

                                "type": "string",

                                "description": 'Location (city)'

                            },

                            "salary_from": {

                                "type": "integer",

                                "description": 'Minimum wage'

                            },

                            "limit": {

                                "type": "integer",

                                "description": 'Number of results (default 10)',

                                "default": 10

                            }

                        },

                        "required": ["query"]

                    }

                },

                {

                    "type": "function",

                    "name": "analyze_candidate",

                    "description": 'Detailed analysis of the candidate and conformity assessment of the position',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "candidate_id": {

                                "type": "string",

                                "description": 'ID candidate for analysis'

                            },

                            "position_requirements": {

                                "type": "string",

                                "description": 'Position requirements for comparison'

                            },

                            "detailed_analysis": {

                                "type": "boolean",

                                "description": 'Perform detailed analysis ( default tree)',

                                "default": True

                            }

                        },

                        "required": ["candidate_id"]

                    }

                },

                {

                    "type": "function",

                    "name": "rank_candidates",

                    "description": 'Early list of candidates according to relevance and relevance',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "candidate_ids": {

                                "type": "array",

                                "items": {"type": "string"},

                                "description": 'List of ID candidates for ranking'

                            },

                            "criteria": {

                                "type": "string",

                                "description": 'Criteria for ranking'

                            },

                            "position_requirements": {

                                "type": "string",

                                "description": 'Position requirements'

                            }

                        },

                        "required": ["candidate_ids", "criteria"]

                    }

                },

                {

                    "type": "function",

                    "name": "post_vacancy",

                    "description": 'Publication of the vacancy on job portals',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "title": {

                                "type": "string",

                                "description": 'Vacancy name'

                            },

                            "description": {

                                "type": "string",

                                "description": 'Vacancy description'

                            },

                            "requirements": {

                                "type": "string",

                                "description": 'Candidates &apos; requirements'

                            },

                            "salary_from": {

                                "type": "integer",

                                "description": 'Pay from'

                            },

                            "salary_to": {

                                "type": "integer",

                                "description": 'Pay before'

                            },

                            "location": {

                                "type": "string",

                                "description": 'Location'

                            }

                        },

                        "required": ["title", "description", "requirements"]

                    }

                },

                {

                    "type": "function",

                    "name": "schedule_interview",

                    "description": 'Planning an interview with the candidate',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "candidate_id": {

                                "type": "string",

                                "description": 'ID candidate'

                            },

                            "interview_type": {

                                "type": "string",

                                "description": 'Type of interview',

                                "enum": ["phone", "video", "onsite", "technical"]

                            },

                            "date": {

                                "type": "string",

                                "description": 'Preferable date (YYYY-MM-DD)'

                            },

                            "duration": {

                                "type": "integer",

                                "description": 'Duration in minutes',

                                "default": 60

                            }

                        },

                        "required": ["candidate_id", "interview_type"]

                    }

                }

            ],

            'rules': {

                "search_focus": "quality_over_quantity",

                "analysis_depth": "detailed",

                "communication": "professional_friendly",

                "delegation": "clear_instructions"

            },

            'tone_of_voice': 'Professional recruiter, friendly, detailed in analysis',

            'training_data': {

                "recruitment_knowledge": 'IT recruitment, talent search, summary analysis',

                "market_understanding": 'IT market, wages, trends',

                "candidate_evaluation": 'Skills assessment, compliance'

            },

            'routing_rules': {

                "managed_by": "@boss.ai",

                "delegates_to": ["@sergei.ai"],

                "reports_to": "@boss.ai"

            },

            'version': '1.0.0'

        }

        

        # === SERGEI.AI (SCRINNER) ===

        sergei_config = {

            'agent_name': '@sergei.ai',

            'role': 'Candidate Scrinner',

            'persona': 'Candidature screen for conformity assessment',

            'system_prompt': "You're @sergei.ai - Demo Candidate 01, expert on IT candidate screening.\n\n\n\nYOUR ROLE AND EXPERTS:\n\nYou're a professional screenr specializing in the evaluation and testing of IT candidates. Your goal is to conduct quality screening and provide detailed reports on candidates.\n\n\n\nYOUR PRINCIPLE FUNCTIONS:\n\n1. ♪ Screen of candidates for position\n\n2. Assessment of technical skills and conformity\n\n3. Analysis of work experience and competencies\n\n4. :: Generation of detailed candidate reports\n\n5. Priority candidates\n\n6. \\Reverse for @demo_organization_alenaaibot\n\n\n\nESTABLISHED INSTRUMENTS:\n\n- screen_candidate: Conduct of screening of the candidate\n\n- assess_skills: Evaluation of technical skills\n\n- generate_report: Generation of candidate report\n\n- rank_candidates: Nomination of candidates\n\n- analyze_experience: Analysis of work experience\n\n\n\nYOUR WORKSHOP:\n\n- Detailed analysis of each candidate\n\n- Objective assessment of skills and experience\n\n- Structured conclusions reports\n\n- Professional recommendations\n\n- Focus on quality assessment\n\n\n\nTHE CONTEXT OF THE BASED:\n\n{conversation_history}\n\n\n\nPRINCIPLES OF RESPONSES:\n\n1. Always answer as a professional screenr\n\n2. Use specific evaluation criteria\n\n3. Provide structured reports\n\n4. Make clear recommendations\n\n5. Be Objective in Evaluations\n\n6. Use professional terminology\n\n\n\nSTRENGTHENING! ONLY WITH SETTLEMENT:\n\n@demo_organization_bossaibot (supervisor)\n\n@demo_organization_alenaaibot (recruiter)\n\n@demo_organization_sergeiaibot (T)\n\nDon't pee! Underline only!\n\n\n\nMANAGEMENT OF WORK:\n\n1. You get screening assignments from @demo_organization_alenaaibot\n\n2. Conducting detailed screening of candidates\n\n3. Assessing position compliance\n\n4. Generate reports with recommendations\n\n5. Send the results to @demo_organization_alenaaibot\n\n6. Report to @demo_organization_bossaibot on results\n\n\n\nCOMMUNICATION:\n\n- You get the job from @demo_organization_alenaaibot\n\n- Send the results to @demo_organization_alenaaibot\n\n- Sending reports @demo_organization_bossaibot\n\n\n\nAnswer in Russian, professionally and with emphasis on the quality of the assessment.",

            'tools': [

                {

                    "type": "function",

                    "name": "screen_candidate",

                    "description": 'Conduct of screening of the candidate for qualifications',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "candidate_id": {

                                "type": "string",

                                "description": 'ID candidate for screening'

                            },

                            "screening_type": {

                                "type": "string",

                                "description": 'Type of screening',

                                "enum": ["technical", "comprehensive", "quick"],

                                "default": "comprehensive"

                            },

                            "position_requirements": {

                                "type": "string",

                                "description": 'Position requirements'

                            },

                            "screening_focus": {

                                "type": "array",

                                "items": {"type": "string"},

                                "description": 'Screen Focus',

                                "default": ["skills", "experience", "fit"]

                            }

                        },

                        "required": ["candidate_id"]

                    }

                },

                {

                    "type": "function",

                    "name": "assess_skills",

                    "description": 'Evaluation of the candidate &apos; s technical skills',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "candidate_id": {

                                "type": "string",

                                "description": 'ID candidate'

                            },

                            "skills_list": {

                                "type": "array",

                                "items": {"type": "string"},

                                "description": 'List of skills for evaluation'

                            },

                            "assessment_level": {

                                "type": "string",

                                "description": 'Level of evaluation',

                                "enum": ["basic", "detailed", "expert"],

                                "default": "detailed"

                            }

                        },

                        "required": ["candidate_id", "skills_list"]

                    }

                },

                {

                    "type": "function",

                    "name": "generate_report",

                    "description": 'Generation of candidate report',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "candidate_id": {

                                "type": "string",

                                "description": 'ID candidate'

                            },

                            "report_type": {

                                "type": "string",

                                "description": 'Type of report',

                                "enum": ["summary", "detailed", "technical"],

                                "default": "detailed"

                            },

                            "include_recommendations": {

                                "type": "boolean",

                                "description": 'Include recommendations',

                                "default": True

                            }

                        },

                        "required": ["candidate_id"]

                    }

                },

                {

                    "type": "function",

                    "name": "rank_candidates",

                    "description": 'Earning of the list of candidates',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "candidate_ids": {

                                "type": "array",

                                "items": {"type": "string"},

                                "description": 'List of ID candidates'

                            },

                            "ranking_criteria": {

                                "type": "string",

                                "description": 'Criteria for ranking'

                            },

                            "position_requirements": {

                                "type": "string",

                                "description": 'Position requirements'

                            }

                        },

                        "required": ["candidate_ids", "ranking_criteria"]

                    }

                },

                {

                    "type": "function",

                    "name": "analyze_experience",

                    "description": 'Analysis of the candidate &apos; s experience',

                    "parameters": {

                        "type": "object",

                        "properties": {

                            "candidate_id": {

                                "type": "string",

                                "description": 'ID candidate'

                            },

                            "experience_focus": {

                                "type": "array",

                                "items": {"type": "string"},

                                "description": 'The focus of the experience analysis',

                                "default": ["relevance", "progression", "achievements"]

                            }

                        },

                        "required": ["candidate_id"]

                    }

                }

            ],

            'rules': {

                "assessment_style": "objective_detailed",

                "report_format": "structured",

                "recommendation_style": "clear_actionable",

                "communication": "professional_analytical"

            },

            'tone_of_voice': 'Professional screenr, analytical, objective',

            'training_data': {

                "screening_knowledge": 'Screening technicians, evaluation of candidates, summary analysis',

                "technical_assessment": 'IT skills assessment, technical interview',

                "report_writing": 'Structured reports, recommendations'

            },

            'routing_rules': {

                "managed_by": "@boss.ai",

                "receives_from": ["@alena.ai"],

                "reports_to": ["@alena.ai", "@boss.ai"]

            },

            'version': '1.0.0'

        }

        

        return {

            'supervisor_001': boss_config,

            'recruiter_001': alena_config,

            'scrinner_001': sergei_config

        }

    

    async def _migrate_agent_config(self, agent_id: str, config: Dict[str, Any]):

        'Migration of one agent configuration'

        try:

            cursor = self.connection.cursor()

            

            # See if the agent already exists.

            cursor.execute("SELECT agent_id FROM agent_configurations WHERE agent_id = %s", (agent_id,))

            if cursor.fetchone():

                logger.info(f"⚠️ Agent {agent_id} already in existence, updated configuration")

                # Update the existing configuration

                update_query = """

                UPDATE agent_configurations SET

                    agent_name = %s, role = %s, persona = %s, system_prompt = %s,

                    tools = %s, rules = %s, tone_of_voice = %s, training_data = %s,

                    routing_rules = %s, version = %s, updated_at = %s

                WHERE agent_id = %s

                """

                cursor.execute(update_query, (

                    config['agent_name'], config['role'], config['persona'], config['system_prompt'],

                    json.dumps(config['tools']), json.dumps(config['rules']), config['tone_of_voice'],

                    json.dumps(config['training_data']), json.dumps(config['routing_rules']),

                    config['version'], datetime.now(), agent_id

                ))

            else:

                # Add a new configuration

                insert_query = """

                INSERT INTO agent_configurations (

                    agent_id, agent_name, role, persona, system_prompt, tools, rules,

                    tone_of_voice, training_data, routing_rules, version, is_active,

                    created_at, updated_at

                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

                """

                cursor.execute(insert_query, (

                    agent_id, config['agent_name'], config['role'], config['persona'],

                    config['system_prompt'], json.dumps(config['tools']), json.dumps(config['rules']),

                    config['tone_of_voice'], json.dumps(config['training_data']),

                    json.dumps(config['routing_rules']), config['version'], True,

                    datetime.now(), datetime.now()

                ))

            

            self.connection.commit()

            cursor.close()

            

        except Error as e:

            logger.error(f"❌ Migration Configuration Error {agent_id}: {e}")

            raise

    

    async def _create_sample_organizational_structure(self):

        'Establishment of examples of organizational structure'

        try:

            cursor = self.connection.cursor()

            

            # Examples of organizational structure

            org_structure = [

                # HR Division

                ("HR", "Recruiting", "HR Director", "Demo Candidate 02", 1, None),

                ("HR", "Recruiting", "Senior Recruiter", 'Elena Smirnova', 2, None),

                ("HR", "Recruiting", "Junior Recruiter", "Demo Candidate 03", 3, None),

                

                # IT Division

                ("IT", "Backend", "CTO", "Demo Candidate 04", 1, None),

                ("IT", "Backend", "Team Lead", "Demo Candidate 05", 2, None),

                ("IT", "Backend", "Senior Developer", "Demo Candidate 06", 3, None),

                ("IT", "Frontend", "Team Lead", "Demo Candidate 07", 2, None),

                ("IT", "Frontend", "Middle Developer", 'Igor Lebedev', 3, None),

                

                # Finance Division

                ("Finance", "Accounting", "CFO", "Demo Candidate 08", 1, None),

                ("Finance", "Accounting", "Senior Accountant", "Demo Candidate 09", 2, None),

                

                # Sales Division

                ("Sales", "Enterprise", "Sales Director", "Demo Candidate 10", 1, None),

                ("Sales", "Enterprise", "Account Manager", 'Tatiana Orlova', 2, None)

            ]

            

            for dept, division, position, full_name, level, manager_id in org_structure:

                cursor.execute("""

                    INSERT IGNORE INTO organizational_structure 

                    (department, division, position, full_name, hierarchy_level, manager_id, created_at, updated_at)

                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)

                """, (dept, division, position, full_name, level, manager_id, datetime.now(), datetime.now()))

            

            self.connection.commit()

            cursor.close()

            logger.info('✅ Organizational structure established')

            

        except Error as e:

            logger.error(f"❌ Error in organizational structure: {e}")

            raise

    

    async def _create_deployed_agents_registry(self):

        'Establishment of a roster of deployed agents'

        try:

            cursor = self.connection.cursor()

            

            # Register of deployed agents

            deployed_agents = [

                ("supervisor_001", "@demo_organization_bossaibot", '{"channels": ["general", "hr_management"]}', "active", '{"max_requests_per_hour": 100}'),

                ("recruiter_001", "@demo_organization_alenaaibot", '{"channels": ["recruiting", "hr_team"]}', "active", '{"max_requests_per_hour": 50}'),

                ("scrinner_001", "@demo_organization_sergeiaibot", '{"channels": ["screening", "hr_team"]}', "active", '{"max_requests_per_hour": 30}')

            ]

            

            for agent_id, teams_identity, channel_roles, status, limits in deployed_agents:

                cursor.execute("""

                    INSERT IGNORE INTO deployed_agents_registry 

                    (agent_id, teams_identity, channel_roles, status, limits, last_activity, created_at, updated_at)

                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)

                """, (agent_id, teams_identity, channel_roles, status, limits, datetime.now(), datetime.now(), datetime.now()))

            

            self.connection.commit()

            cursor.close()

            logger.info('✅ Register of deployed agents established')

            

        except Error as e:

            logger.error(f"❌ Error in creating a register of agents: {e}")

            raise



async def main():

    'Main function of migration'

    # Logging settings

    logging.basicConfig(

        level=logging.INFO,

        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    )

    

    # PostgreSQL database configuration

    db_config = {

        'host': 'localhost',

        'port': 5432,

        'user': 'office_services_user',

        'password': os.environ["SERVICES_CENTRAL_POSTGRES_ENVIRONMENT_POSTGRES_PASSWORD"],

        'database': 'office_services_agents'

    }

    

    migrator = AgentConfigMigrator(db_config)

    

    try:

        await migrator.connect()

        await migrator.migrate_all_agents()

        logger.info('🎉 Migration successfully completed!')

    except Exception as e:

        logger.error(f"💥 Critical Migration Error: {e}")

    finally:

        migrator.disconnect()



if __name__ == "__main__":

    asyncio.run(main())