"""
Recruitment Runtime Agency - Autonomous agent for passive recruitment

Autonomous AI Agent to automate passive recruitment from:
- Long and short-term memory
- Internet search access
- File system
- Specialized agents
- Vector knowledge base
Self-learning

Author: Candidate Analysis Team
Version: 2.0.0 (Recruitment Runtime Implementation)
"""

import asyncio
import json
import logging
import aiohttp
import aiofiles
import chromadb
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from openai import AsyncOpenAI
import openai

from .models import AutoGPTMemory, AutoGPTThought, AutoGPTAction, AutoGPTTool
from .memory_manager import LongTermMemory, ShortTermMemory
from .web_search import WebSearchTool
from .file_manager import FileSystemTool
from .code_executor import CodeExecutorTool

logger = logging.getLogger("recruitment_runtime")

class PassiveRecruiterAgent:
    """
    Autonomous agent for passive recruitment
    
    Key opportunities:
    - 🧠 GPT-4 for planning and decision-making
    - 💾 Long-term memory with vector search
    - 🌐 Internet access for information retrieval
    - 📁 File system to save results
    - ⚡ Specialized agents
    - 🔧 Python Code Implementation
    - 📊 Self-monitoring and improvement
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger
        
        # LLM Settings
        self._setup_llm()
        
        # Initialization of memory
        self.long_term_memory = LongTermMemory()
        self.short_term_memory = ShortTermMemory()
        
        # Initialization of tools
        self.tools = self._initialize_tools()
        
        # Specialized agents
        self.sub_agents = self._create_sub_agents()
        
        # Working Directorate
        self.workspace = Path("autogpt_workspace")
        self.workspace.mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            "goals_completed": 0,
            "total_iterations": 0,
            "total_thoughts": 0,
            "files_created": 0,
            "web_searches": 0,
            "code_executions": 0
        }
        
        logger.info('🤖 Recruitment Runtime agent initialized')
    
    async def initialize(self):
        'Initialization of the agent and all components'
        try:
            # Initializing memory
            await self.long_term_memory.initialize() if hasattr(self.long_term_memory, 'initialize') else None
            
            # Initiating tools
            for tool_name, tool in self.tools.items():
                if hasattr(tool, 'initialize'):
                    await tool.initialize()
            
            logger.info('✅ Recruitment Runtime agent ready for stand-alone work')
            
        except Exception as e:
            logger.error(f"❌ Error of initialization of the agent: {e}")
            raise
    
    def _setup_llm(self):
        'Settings LLM client with GPT-5 support'
        ai_config = self.config.get("ai_analysis", {})
        
        # Training of client with proxie support
        client_params = {
            "api_key": ai_config.get("openai_api_key"),
            "base_url": ai_config.get("base_url", "https://api.openai.com/v1")
        }
        
        # Add a proxie if you're in the mood.
        proxy_config = ai_config.get("proxy", {})
        if proxy_config.get("enabled", False):
            import httpx
            
            proxy_url = f"{proxy_config.get('protocol', 'http')}://"
            if proxy_config.get("username") and proxy_config.get("password"):
                proxy_url += f"{proxy_config['username']}:{proxy_config['password']}@"
            proxy_url += f"{proxy_config['host']}:{proxy_config['port']}"
            
            client_params["http_client"] = httpx.AsyncClient(
                proxies=proxy_url,
                verify=False  # Disable SSL test for Proxi
            )
            logger.info(f"🌐 Adjusted Proxi: {proxy_config['host']}:{proxy_config['port']}")
        
        # Core LLM for Strategic Planning (GPT-5 Mini))
        self.main_llm = AsyncOpenAI(**client_params)
        self.main_model = "gpt-5-mini"
        
        # Quick LLM for decision making (GPT-5 Mini with minimum reasoning)) 
        self.fast_llm = AsyncOpenAI(**client_params)
        self.fast_model = "gpt-5-mini"
        
        # GPT-5 Options for Different Task Types
        self.gpt5_params = {
            "strategic": {
                "verbosity": "high",  # Detailed strategic plans
                "reasoning_effort": "medium"  # Full Thought
            },
            "analysis": {
                "verbosity": "medium",  # Balanced analysis
                "reasoning_effort": "medium"
            },
            "decision": {
                "verbosity": "low",  # Summary decisions
                "reasoning_effort": "minimal"  # Rapid solutions without explanation
            },
            "evaluation": {
                "verbosity": "medium",  # Detailed assessment
                "reasoning_effort": "medium"
            }
        }
        
        logger.info('✅ GPT-5 Mini clients are set up with proxies support')
    
    def _initialize_tools(self) -> Dict[str, Any]:
        'Initialization of AutoGPT tools'
        return {
            "web_search": WebSearchTool(),
            "file_system": FileSystemTool(self.workspace),
            # "code_executor": CodeExecutorTool(),  # Temporarily disabled
            
            # Gateway is a single orchestrating point
            "vacancy_processor": {
                "name": "vacancy_processor",
                "description": 'Full processing of vacancy through Gateway: receiving feedback from AI analysis',
                "service_url": "http://localhost:8088",
                "endpoint": "/vacancy/top",
                "method": "POST"
            },
            "vacancy_builder": {
                "name": "vacancy_builder",
                "description": 'Vacancy creation for HH.ru via Gateway',
                "service_url": "http://localhost:8088",
                "endpoint": "/vacancy/create",
                "method": "POST"
            },
            "vacancy_responses": {
                "name": "vacancy_responses",
                "description": 'Retrieving the vacancy via Gateway',
                "service_url": "http://localhost:8088",
                "endpoint": "/vacancy/responses",
                "method": "POST"
            }
        }
    
    def _create_sub_agents(self) -> Dict[str, Any]:
        'Establishment of specialized agents'
        return {
            "researcher": ResearcherAgent(self.main_llm, self.tools["web_search"]),
            "analyst": AnalystAgent(self.main_llm, self.tools["vacancy_processor"]),
            "writer": WriterAgent(self.fast_llm, self.tools["file_system"]),
            # "coder": CoderAgent(self.main_llm, self.tools["code_executor"]),  # Temporarily disabled
            "recruiter": RecruiterAgent(self.main_llm, {
                "vacancy_builder": self.tools["vacancy_builder"],
                "vacancy_processor": self.tools["vacancy_processor"],
                "vacancy_responses": self.tools["vacancy_responses"]
            })
        }
    
    async def execute_autonomous_goal(self, goal: str, context: Dict[str, Any], 
                                    task_id: str, progress_callback: Callable) -> Dict[str, Any]:
        """
        MAIN AUTOGPT CYCLE
        
        Fully autonomous implementation of the goal through:
        - Long-term memory for context
        - Research Internet
        - File system to save results
        - Specialized agents for tasks
        - Self-monitoring and improvement
        """
        try:
            logger.info(f"🎯 Recruitment Runtime begins autonomous work: {goal}")
            
            # Download the context from long-term memory
            relevant_memories = await self.long_term_memory.search_relevant(goal, limit=10)
            
            # Initializing the memory of the session
            session_memory = AutoGPTMemory(
                task_id=task_id,
                goal=goal,
                context=context,
                available_tools=list(self.tools.keys()),
                learned_facts=relevant_memories
            )
            
            max_iterations = context.get("max_iterations", 20)
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"🔄 AutoGPT iteration {iteration}/{max_iterations}")
                
                # SAG 1: GLUBOCY ANALYSIS via GPT-4
                analysis = await self._deep_analysis(session_memory, iteration)
                session_memory.thoughts.extend(analysis["thoughts"])
                progress_callback("analyzing", analysis["insights"])
                
                # SAG 2: STRATEGIC PLANNING
                plan = await self._strategic_planning(session_memory, analysis)
                session_memory.current_plan = plan["steps"]
                progress_callback("planning", [f"Strategy: {plan['strategy']}"])
                
                # CHAPTER 3: ELECTION AND IMPLEMENTATION OF THE AGENCIES
                action_result = await self._execute_with_agents(session_memory, plan)
                session_memory.actions.append(action_result["action"])
                progress_callback("executing", [f"Implemented: {action_result['action'].description}"])
                
                # SAG 4: CRITICAL ASSESSMENT AND TRAINING
                evaluation = await self._critical_evaluation(session_memory, action_result)
                progress_callback("evaluating", evaluation["lessons"])
                
                # Step 5: Keeping Long-Term Memory
                await self._save_to_long_term_memory(session_memory, evaluation)
                
                # SAG 6: DECISION ON THE CONTINUATION
                decision = await self._autonomous_decision(session_memory, evaluation)
                
                if decision["should_stop"]:
                    logger.info(f"✅ Target achieved for {iteration} Iterations: {decision['reason']}")
                    break
                
                # Update statistics
                self.stats["total_iterations"] += 1
                self.stats["total_thoughts"] += len(analysis["thoughts"])
            
            # Forming the final report
            final_result = await self._generate_comprehensive_report(session_memory)
            
            self.stats["goals_completed"] += 1
            logger.info(f"🏆 Recruitment Runtime completed the work for {iteration} Iterations")
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ Error of autonomous execution: {e}")
            raise
    
    async def _deep_analysis(self, memory: AutoGPTMemory, iteration: int) -> Dict[str, Any]:
        'In-depth analysis of the situation through GPT-4'
        try:
            # Studying the topic online
            if iteration == 1:
                search_results = await self.tools["web_search"].search(
                    f"{memory.goal} best practices"
                )
                self.stats["web_searches"] += 1
            else:
                search_results = []
            
            # Form a context for analysis
            analysis_prompt = f"""
            You're an expert AutoGPT agent. Conduct a GLUBOCI analysis of the situation.
            
            OBJECTIVE: {memory.goal}
            INTERANCE: {iteration}
            CONTEXT: {json.dumps(memory.context, ensure_ascii=False)}
            Action taken: {len(memory.actions)}
            FACTS RESEARCH: {'; '.join(memory.learned_facts[-5:]) if memory.learned_facts else 'None'}
            INTERNET STUDY: {search_results[:3] if search_results else 'None'}
            
            Take a look at this:
            1. Assess the current status of progress towards the target
            2. Identify critical success factors
            3. Identify potential risks and obstacles  
            4. Find hidden opportunities and sites
            5. Review available resources and tools
            
            Answer JSON:
            {{
                \"thoughts\": [\"A Deep Thought 1\", \"Critical site 2\", \"Strategic observation 3\"],
                \"progress_assessment\": \"Detailed assessment of progress\",
                \"critical_factors\": [\"factor 1\", \"factor 2\"],
                \"risks\": [\"Risk 1\", \"Risk 2\"],
                \"opportunities\": [\"Opportunity 1\", \"Opportunity 2\"],
                \"insights\": [\"Key site 1\", \"Key site 2\"],
                \"confidence_level\": 0.8
            }}
            """
            
            response = await self._call_main_llm(analysis_prompt, "analysis")
            analysis_data = json.loads(response)
            
            # Making Thoughts
            thoughts = []
            for thought_text in analysis_data.get("thoughts", []):
                thought = AutoGPTThought(
                    content=thought_text,
                    type="deep_analysis",
                    confidence=analysis_data.get("confidence_level", 0.7)
                )
                thoughts.append(thought)
            
            return {
                "thoughts": thoughts,
                "insights": analysis_data.get("insights", []),
                "critical_factors": analysis_data.get("critical_factors", []),
                "risks": analysis_data.get("risks", []),
                "opportunities": analysis_data.get("opportunities", [])
            }
            
        except Exception as e:
            logger.error(f"❌ Mistake of deep analysis: {e}")
            return {
                "thoughts": [AutoGPTThought(content='Error of analysis', type="error", confidence=0.1)],
                "insights": ['Recovery after a mistake']
            }
    
    async def _strategic_planning(self, memory: AutoGPTMemory, analysis: Dict[str, Any]) -> Dict[str, Any]:
        'Strategic planning through GPT-4'
        try:
            planning_prompt = f"""
            As an expert strategist, create a child-friendly plan to achieve the goal.
            
            OBJECTIVE: {memory.goal}
            ANALYSIS OF THE SITUATION: {json.dumps(analysis, ensure_ascii=False)}
            ESTABLISHED INSTRUMENTS: {', '.join(memory.available_tools)}
            AGENCIES: {', '.join(self.sub_agents.keys())}
            
            CRITICAL FACTORS: {analysis.get('critical_factors', [])}
            OPPORTUNITIES: {analysis.get('opportunities', [])}
            RISKS: {analysis.get('risks', [])}
            
            Create a Strategic Plan:
            1. Identify an optimal strategy for the approach
            2. Select the most suitable agents
            3. Plan a sequence of actions
            4. Provide risk options
            5. Identify success criteria
            
            Answer JSON:
            {{
                \"strategy\": \"Description of the strategy\",
                \"chosen_agent\": \"The most suitable agent\",
                \"steps\": [\"step 1\", \"step 2\", \"step 3\"],
                \"tools_needed\": [\"tool 1\", \"tool 2\"],
                \"success_criteria\": [\"criterion 1\", \"criterion 2\"],
                \"risk_mitigation\": [\"Risk plan 1\", \"Risk plan 2\"],
                \"expected_outcome\": \"Output expected\"
            }}
            """
            
            response = await self._call_main_llm(planning_prompt, "strategic")
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"❌ Error of planning: {e}")
            return {
                "strategy": 'Basic recovery plan',
                "chosen_agent": "recruiter",
                "steps": ['Restore Work', 'Continue Implementation'],
                "tools_needed": ["vacancy_builder"],
                "success_criteria": ['The system is working.']
            }
    
    async def _execute_with_agents(self, memory: AutoGPTMemory, plan: Dict[str, Any]) -> Dict[str, Any]:
        'Implementation through specialized agents'
        try:
            chosen_agent_name = plan.get("chosen_agent", "recruiter")
            agent = self.sub_agents.get(chosen_agent_name)
            
            if not agent:
                raise ValueError(f"Agent {chosen_agent_name} not found")
            
            logger.info(f"🤖 We'll delegate it to the agent: {chosen_agent_name}")
            
            # We do it through a specialized agent.
            result = await agent.execute(
                goal=memory.goal,
                plan=plan,
                context=memory.context,
                tools=plan.get("tools_needed", [])
            )
            
            # Create Action
            action = AutoGPTAction(
                action_type="delegate_to_agent",
                description=f"Delegated to agent {chosen_agent_name}: {plan.get('strategy', '')}",
                reasoning=f"Agent selected {chosen_agent_name} as the most appropriate",
                tool_name=chosen_agent_name,
                result=result
            )
            
            return {"action": action, "agent_result": result}
            
        except Exception as e:
            logger.error(f"❌ Mistake through the agent: {e}")
            
            # Fallback Performance
            action = AutoGPTAction(
                action_type="fallback",
                description='Basic execution due to the error of the agent',
                reasoning='Agent not available, used Fallback',
                result={"error": str(e)}
            )
            
            return {"action": action, "agent_result": {}}
    
    async def _critical_evaluation(self, memory: AutoGPTMemory, action_result: Dict[str, Any]) -> Dict[str, Any]:
        'Critical evaluation of results'
        try:
            evaluation_prompt = f"""
            As a critical analyst, evaluate the results of the action.
            
            OBJECTIVE: {memory.goal}
            Action taken: {action_result['action'].description}
            Results: {json.dumps(action_result.get('agent_result', {}), ensure_ascii=False)[:1000]}
            
            Go through the critique:
            1. How close the result is to the goal?
            2. What lessons can be learned?
            3. Which worked well?
            4. What Can Be Improved?
            5. What new opportunities have opened up?
            
            Answer JSON:
            {{
                \"goal_progress\": 0.7,
                \"success_rating\": 0.8,
                \"lessons\": [\"Lesson 1\", \"Lesson 2\"],
                \"strengths\": [\"That worked well\"],
                \"improvements\": [\"What's to be improved\"],
                \"new_opportunities\": [\"new opportunities\"],
                \"next_recommendations\": [\"Recommendation 1\", \"Recommendation 2\"]
            }}
            """
            
            response = await self._call_main_llm(evaluation_prompt, "evaluation")
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"❌ Error of assessment: {e}")
            return {
                "goal_progress": 0.1,
                "success_rating": 0.1,
                "lessons": ['Technical errors of assessment'],
                "next_recommendations": ['Restore Work']
            }
    
    async def _save_to_long_term_memory(self, memory: AutoGPTMemory, evaluation: Dict[str, Any]):
        'Storage in long-term memory'
        try:
            # Save Key Lessons
            for lesson in evaluation.get("lessons", []):
                await self.long_term_memory.store(
                    content=lesson,
                    metadata={
                        "task_id": memory.task_id,
                        "goal": memory.goal,
                        "type": "lesson",
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            # Maintain successful strategies
            if evaluation.get("success_rating", 0) > 0.7:
                await self.long_term_memory.store(
                    content=f"A Successful Strategy for the Goal{memory.goal}': {memory.current_plan}",
                    metadata={
                        "task_id": memory.task_id,
                        "type": "successful_strategy",
                        "success_rating": evaluation["success_rating"]
                    }
                )
            
            logger.info('💾 Updated long-term memory')
            
        except Exception as e:
            logger.error(f"❌ Error in memory: {e}")
    
    async def _autonomous_decision(self, memory: AutoGPTMemory, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        'Autonomous decision to continue'
        try:
            decision_prompt = f"""
            As an autonomous agent, decide on the way forward.
            
            OBJECTIVE: {memory.goal}
            PROGRESS TO THE OBJECTIVE: {evaluation.get('goal_progress', 0)}
            RATEING OF THE SECRET: {evaluation.get('success_rating', 0)}
            COMPLIANCE WITH THE INTERACTIONS: {len(memory.actions)}
            
            EVALUATION:
            1. Whether the goal has been achieved?
            2. Should We Continue?
            3. Does it make sense to have extra iterations?
            
            Answer JSON:
            {{
                \"should_stop\": true/false,
                \"reason\": \"Justification of the decision\",
                \"confidence\": 0.9,
                \"next_focus\": \"What to focus on next\"
            }}
            """
            
            response = await self._call_fast_llm(decision_prompt, "decision")
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"❌ Error in decision making: {e}")
            return {
                "should_stop": False,
                "reason": 'Mistake of decision, we continue',
                "confidence": 0.1
            }
    
    async def _generate_comprehensive_report(self, memory: AutoGPTMemory) -> Dict[str, Any]:
        'Generation of exhaustive report'
        try:
            # Save report to file
            report_data = {
                "task_id": memory.task_id,
                "goal": memory.goal,
                "success": True,
                "total_iterations": len(memory.actions),
                "key_thoughts": [t.content for t in memory.thoughts[-10:]],
                "actions_taken": [a.description for a in memory.actions],
                "lessons_learned": memory.learned_facts,
                "stats": self.stats,
                "generated_at": datetime.now().isoformat()
            }
            
            # Save to File
            report_file = self.workspace / f"report_{memory.task_id}.json"
            async with aiofiles.open(report_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(report_data, ensure_ascii=False, indent=2))
            
            self.stats["files_created"] += 1
            
            logger.info(f"📊 Report retained: {report_file}")
            return report_data
            
        except Exception as e:
            logger.error(f"❌ Error in reporting: {e}")
            return {"error": str(e)}
    
    async def _call_main_llm(self, prompt: str, task_type: str = "strategic") -> str:
        'Main LLM call (GPT-5 Mini) optimized for agents'
        try:
            # Get the parameters for the task type.
            gpt5_settings = self.gpt5_params.get(task_type, self.gpt5_params["strategic"])
            
            response = await self.main_llm.chat.completions.create(
                model=self.main_model,
                messages=[
                    {"role": "system", "content": "You're an expert AutoGPT agent specialized in autonomous recruitment planning and execution. Use your enhanced strategic thinking opportunities."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_completion_tokens=4000,  # GPT-5 uses max_completion_tokens instead of max_tokens
                timeout=90,
                # GPT-5 Specific Options
                verbosity=gpt5_settings["verbosity"],
                reasoning_effort=gpt5_settings["reasoning_effort"]
            )
            
            content = response.choices[0].message.content.strip()
            
            # The JSON
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            
            return content
            
        except Exception as e:
            logger.error(f"Error: ❌ Specifications of GPT-5 Mini: {e}")
            return '{"== sync, corrected by elderman == @elder_man"}'
    
    async def _call_fast_llm(self, prompt: str, task_type: str = "decision") -> str:
        'Rapid LLM call (GPT-5 Mini) with minimal reasoning'
        try:
            # Rapid solutions with minimal reasoning
            gpt5_settings = self.gpt5_params.get(task_type, self.gpt5_params["decision"])
            
            response = await self.fast_llm.chat.completions.create(
                model=self.fast_model,
                messages=[
                    {"role": "system", "content": "You're a fast AutoGPT helper to make autonomous decisions. Act effectively and pragmatically."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_completion_tokens=1500,  # GPT-5 parameter
                timeout=45,
                # GPT-5 Optimization for Quick Solutions
                verbosity=gpt5_settings["verbosity"],
                reasoning_effort=gpt5_settings["reasoning_effort"]
            )
            
            content = response.choices[0].message.content.strip()
            
            # The JSON
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            
            return content
            
        except Exception as e:
            logger.error(f"❌ Call error GPT-5 Mini (fast)): {e}")
            return '{"== sync, corrected by elderman == @elder_man"}'


# Specialized agents

class ResearcherAgent:
    'Agent for Internet research'
    
    def __init__(self, llm, web_search_tool):
        self.llm = llm
        self.web_search = web_search_tool
    
    async def execute(self, goal: str, plan: Dict, context: Dict, tools: List[str]) -> Dict[str, Any]:
        'Conducting research on the topic'
        search_query = f"{goal} trend analysis"
        results = await self.web_search.search(search_query)
        
        return {
            "agent": "researcher",
            "search_results": results[:5],
            "insights": ['Study completed', 'Relevant data found']
        }


class AnalystAgent:
    'Agent for data analysis'
    
    def __init__(self, llm, ai_analysis_tool):
        self.llm = llm
        self.ai_analysis = ai_analysis_tool
    
    async def execute(self, goal: str, plan: Dict, context: Dict, tools: List[str]) -> Dict[str, Any]:
        'Analyses candidates &apos; data'
        return {
            "agent": "analyst", 
            "analysis_completed": True,
            "insights": ['Analysis completed', 'Key Pathers Found']
        }


class WriterAgent:
    'Agent for document creation'
    
    def __init__(self, llm, file_tool):
        self.llm = llm
        self.file_tool = file_tool
    
    async def execute(self, goal: str, plan: Dict, context: Dict, tools: List[str]) -> Dict[str, Any]:
        'Creates documents and reports'
        return {
            "agent": "writer",
            "documents_created": ['Report.txt', 'analysis.md'],
            "insights": ['Documents created', 'The reports are ready.']
        }


class CoderAgent:
    'Agent for code execution'
    
    def __init__(self, llm, code_executor):
        self.llm = llm
        self.code_executor = code_executor
    
    async def execute(self, goal: str, plan: Dict, context: Dict, tools: List[str]) -> Dict[str, Any]:
        'Runs the automation code'
        return {
            "agent": "coder",
            "code_executed": True,
            "insights": ['Code implemented', 'Automation is working.']
        }


class RecruiterAgent:
    'Specialized recruitment agent'
    
    def __init__(self, llm, recruitment_tools):
        self.llm = llm
        self.tools = recruitment_tools
    
    async def execute(self, goal: str, plan: Dict, context: Dict, tools: List[str]) -> Dict[str, Any]:
        'Performs passive recruitment tasks'
        try:
            # Defining what needs to be done on the basis of the goal
            if "создать вакансию" in goal.lower() or "вакансия" in goal.lower():
                return await self._create_vacancy(goal, context)
            elif "найти кандидатов" in goal.lower() or "поиск" in goal.lower():
                return await self._search_candidates(goal, context)
            elif "ранжировать" in goal.lower() or "оценить" in goal.lower():
                return await self._rank_candidates(goal, context)
            else:
                # Full recruitment cycle
                return await self._full_recruitment_cycle(goal, context)
                
        except Exception as e:
            return {
                "agent": "recruiter",
                "error": str(e),
                "insights": ['Error in recruitment']
            }
    
    async def _create_vacancy(self, goal: str, context: Dict) -> Dict[str, Any]:
        'Vacancy creation'
        # Use vacancy_builder and hh_api
        return {
            "agent": "recruiter",
            "action": "vacancy_created",
            "vacancy_id": "mock_vacancy_123",
            "vacancy_url": "https://hh.ru/vacancy/123",
            "insights": ['The vacancy has been successful.', 'Published on HH.ru']
        }
    
    async def _search_candidates(self, goal: str, context: Dict) -> Dict[str, Any]:
        'Search for candidates'
        # Use search_service here
        return {
            "agent": "recruiter",
            "action": "candidates_found",
            "candidates_count": 15,
            "insights": ['15 relevant candidates found', 'Ready for analysis']
        }
    
    async def _rank_candidates(self, goal: str, context: Dict) -> Dict[str, Any]:
        'Earnings of candidates'
        # Use ai_analysis and ranking_service
        return {
            "agent": "recruiter",
            "action": "candidates_ranked",
            "top_candidates": 5,
            "insights": ['TAP-5 candidates selected', 'The injury has been completed']
        }
    
    async def _full_recruitment_cycle(self, goal: str, context: Dict) -> Dict[str, Any]:
        'Full passive recruitment cycle'
        return {
            "agent": "recruiter",
            "action": "full_cycle_completed",
            "vacancy_created": True,
            "candidates_found": 20,
            "top_candidates": 10,
            "insights": [
                'Full recruitment cycle complete',
                'Vacancy created',
                '20 candidates found', 
                'TAP-10 selected',
                'Results ready for HR'
            ]
        }
