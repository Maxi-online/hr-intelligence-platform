"""
Organization Context Manager - Management of the context of the organization

Responsible for understanding organization structure, business processes,
culture and rules for decision-making by a master agent.

Author: Candidate Analysis Team
Version: 1.0.0
"""

import json
import os
import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .models import OrganizationContext, WorkflowRule

logger = logging.getLogger("organization-context")


class OrganizationContextManager:
    """
    Manager of the organization &apos; s context
    
    Functions:
    - Loading and managing the organization &apos; s context
    - Understanding the structure and processes
    - Application of business rules
    - Adaptation to corporate culture
    - Updating the context on the basis of experience
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger
        
        # Paths to configuration files
        self.context_file = Path(os.environ.get("ORGANIZATION_CONTEXT_PATH", "config/organization_context.yaml"))
        self.rules_file = Path(os.environ.get("WORKFLOW_RULES_PATH", "config/workflow_rules.yaml"))
        
        # Current context
        self.current_context: Optional[OrganizationContext] = None
        self.workflow_rules: List[WorkflowRule] = []
        
        # Cash for rapid access
        self.departments_cache: Dict[str, Dict[str, Any]] = {}
        self.roles_cache: Dict[str, Dict[str, Any]] = {}
        self.process_cache: Dict[str, Dict[str, Any]] = {}
        
        # Statistics on use
        self.stats = {
            "context_loads": 0,
            "rule_applications": 0,
            "context_updates": 0,
            "cache_hits": 0
        }
    
    async def initialize(self):
        'Initialization of the Context Manager'
        try:
            # Loading the context of the organization
            await self._load_organization_context()
            
            # Loading of operating rules
            await self._load_workflow_rules()
            
            # Cache building
            await self._build_caches()
            
            self.logger.info('✅ OrganizationContext Manager initialized')
            
        except Exception as e:
            self.logger.error(f"Error: ❌ Initialization of Organization Context Manager: {e}")
            # Creating a basic context
            await self._create_default_context()
    
    async def _load_organization_context(self):
        'uploading the organization context from the file'
        try:
            if self.context_file.exists():
                with open(self.context_file, 'r', encoding='utf-8') as f:
                    context_data = yaml.safe_load(f)
                    self.current_context = OrganizationContext(**context_data)
                    self.stats["context_loads"] += 1
                    self.logger.info(f"✅ The context of the organization is up-to-date: {self.current_context.company_name}")
            else:
                self.logger.warning('⚠️ The organization context file is not found, creating a base')
                await self._create_default_context()
                
        except Exception as e:
            self.logger.error(f"❌ Error in the organization's context: {e}")
            await self._create_default_context()
    
    async def _load_workflow_rules(self):
        'uploading of business process rules'
        try:
            if self.rules_file.exists():
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    rules_data = yaml.safe_load(f)
                    
                    self.workflow_rules = [
                        WorkflowRule(**rule_data) for rule_data in rules_data.get("rules", [])
                    ]
                    
                    self.logger.info(f"✅ Loaded {len(self.workflow_rules)} Business process rules")
            else:
                self.logger.info("📝 The rule file is not found, I'm creating the basic rules")
                await self._create_default_rules()
                
        except Exception as e:
            self.logger.error(f"❌ Error in the rules: {e}")
            await self._create_default_rules()
    
    async def _create_default_context(self):
        """Use a fictional fallback without overwriting an existing private file."""
        self.current_context = OrganizationContext(
            company_name="Demonstration Organization",
            industry="Fictional integration example",
            company_size="Demonstration only",
        )
        if not self.context_file.exists():
            await self._save_context()
        self.logger.info("Created a fictional organization fallback")
    
    async def _create_default_rules(self):
        'Establishment of basic business rules'
        try:
            default_rules = [
                WorkflowRule(
                    rule_id="auto_screening",
                    name='Automatic screening',
                    condition={
                        "event": "new_application",
                        "application_count": {"$lt": 10}
                    },
                    action={
                        "type": "delegate_task",
                        "agent": "screener",
                        "priority": "normal"
                    },
                    priority=1,
                    created_by="system"
                ),
                WorkflowRule(
                    rule_id="urgent_hiring",
                    name='Urgent employment',
                    condition={
                        "task_priority": "urgent",
                        "department": "development"
                    },
                    action={
                        "type": "escalate",
                        "notify": ["hr_manager", "hiring_manager"],
                        "sla_override": "24_hours"
                    },
                    priority=3,
                    created_by="system"
                ),
                WorkflowRule(
                    rule_id="quality_check",
                    name='Quality assurance',
                    condition={
                        "task_completed": True,
                        "success_rate": {"$lt": 0.8}
                    },
                    action={
                        "type": "quality_review",
                        "agent": "quality_controller",
                        "escalate_to": "hr_manager"
                    },
                    priority=2,
                    created_by="system"
                )
            ]
            
            for rule in default_rules:
                rule.active = False
            self.workflow_rules = default_rules
            
            # Save to File
            await self._save_rules()
            
            self.logger.info(f"✅ Established {len(default_rules)} of the basic rules")
            
        except Exception as e:
            self.logger.error(f"❌ Error in creating basic rules: {e}")
    
    async def get_context(self) -> OrganizationContext:
        'Getting the current context of the organization'
        if self.current_context is None:
            await self._load_organization_context()
        
        return self.current_context
    
    async def update_context(self, updates: Dict[str, Any]) -> bool:
        'Updating the organization &apos; s context'
        try:
            if self.current_context is None:
                await self._load_organization_context()
            
            # Application of updates
            context_dict = self.current_context.dict()
            
            for key, value in updates.items():
                if key in context_dict:
                    context_dict[key] = value
                    self.logger.info(f"✅ Updated {key} in the context of the organization")
            
            # Time update
            context_dict["last_updated"] = datetime.now()
            
            # Creating a new context
            self.current_context = OrganizationContext(**context_dict)
            
            # Saving
            await self._save_context()
            
            # Renovation of Cashes
            await self._build_caches()
            
            self.stats["context_updates"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Errors in the update of the context: {e}")
            return False
    
    async def get_department_info(self, department_id: str) -> Optional[Dict[str, Any]]:
        'Getting Division Information'
        if department_id in self.departments_cache:
            self.stats["cache_hits"] += 1
            return self.departments_cache[department_id]
        
        if self.current_context:
            for dept in self.current_context.departments:
                if dept.get("id") == department_id:
                    return dept
        
        return None
    
    async def get_role_permissions(self, role_name: str) -> List[str]:
        'Accepting the role'
        if role_name in self.roles_cache:
            self.stats["cache_hits"] += 1
            return self.roles_cache[role_name].get("permissions", [])
        
        if self.current_context and role_name in self.current_context.roles:
            return self.current_context.roles[role_name].get("permissions", [])
        
        return []
    
    async def check_approval_required(self, action: str, context: Dict[str, Any]) -> Optional[str]:
        'Verification of need for approval for action'
        if not self.current_context:
            return None
        
        approval_chains = self.current_context.approval_chains
        hiring_process = self.current_context.hiring_process
        
        # Recruitment review
        if "approvals" in hiring_process:
            required_role = hiring_process["approvals"].get(action)
            if required_role:
                return required_role
        
        # Verification of the chain of approval
        if action in approval_chains:
            # Returning the First Role in the Chain
            chain = approval_chains[action]
            if chain and len(chain) > 0:
                return chain[0]
        
        return None
    
    async def apply_workflow_rules(self, event: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        'Application of business rules'
        try:
            applied_rules = []
            
            for rule in self.workflow_rules:
                if not rule.active:
                    continue
                
                # Verification of the terms and conditions of the rule
                if await self._check_rule_condition(rule, event, context):
                    # Application
                    action_result = await self._apply_rule_action(rule, context)
                    
                    applied_rules.append({
                        "rule_id": rule.rule_id,
                        "rule_name": rule.name,
                        "action_result": action_result,
                        "priority": rule.priority
                    })
                    
                    self.stats["rule_applications"] += 1
                    self.logger.info(f"✅ Rule applied: {rule.name}")
            
            # Priority Sorting
            applied_rules.sort(key=lambda x: x["priority"], reverse=True)
            
            return applied_rules
            
        except Exception as e:
            self.logger.error(f"❌ Mistake of rules: {e}")
            return []
    
    async def _check_rule_condition(self, rule: WorkflowRule, event: str, context: Dict[str, Any]) -> bool:
        'Verification of the terms and conditions of the rule'
        try:
            condition = rule.condition
            
            # A simple verification of the event
            if "event" in condition and condition["event"] != event:
                return False
            
            # Verification of other conditions
            for key, expected_value in condition.items():
                if key == "event":
                    continue
                
                if key not in context:
                    return False
                
                actual_value = context[key]
                
                # Support for comparison operators
                if isinstance(expected_value, dict):
                    for operator, op_value in expected_value.items():
                        if operator == "$lt" and actual_value >= op_value:
                            return False
                        elif operator == "$gt" and actual_value <= op_value:
                            return False
                        elif operator == "$eq" and actual_value != op_value:
                            return False
                else:
                    if actual_value != expected_value:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failure to verify the rules: {e}")
            return False
    
    async def _apply_rule_action(self, rule: WorkflowRule, context: Dict[str, Any]) -> Dict[str, Any]:
        'Application of the rule'
        try:
            action = rule.action
            action_type = action.get("type")
            
            if action_type == "delegate_task":
                return {
                    "action": "delegate_task",
                    "agent": action.get("agent"),
                    "priority": action.get("priority", "normal"),
                    "context": context
                }
            elif action_type == "escalate":
                return {
                    "action": "escalate",
                    "notify": action.get("notify", []),
                    "sla_override": action.get("sla_override"),
                    "context": context
                }
            elif action_type == "quality_review":
                return {
                    "action": "quality_review",
                    "agent": action.get("agent"),
                    "escalate_to": action.get("escalate_to"),
                    "context": context
                }
            else:
                return {
                    "action": "unknown",
                    "raw_action": action,
                    "context": context
                }
                
        except Exception as e:
            self.logger.error(f"❌ Mistake of the rules: {e}")
            return {"action": "error", "error": str(e)}
    
    async def _build_caches(self):
        'Building caches for rapid access'
        try:
            if not self.current_context:
                return
            
            # Cash Divisions
            self.departments_cache = {
                dept.get("id", ""): dept 
                for dept in self.current_context.departments
                if dept.get("id")
            }
            
            # Cash Roles
            self.roles_cache = self.current_context.roles.copy()
            
            # Process Cash
            self.process_cache = {
                "hiring": self.current_context.hiring_process,
                "approvals": self.current_context.approval_chains,
                "sla": self.current_context.sla_requirements
            }
            
            self.logger.info('✅ Cash context built')
            
        except Exception as e:
            self.logger.error(f"❌ Errors of Cache Building: {e}")
    
    async def _save_context(self):
        'Save context to file'
        try:
            if not self.current_context:
                return
            
            # Creation of a directory if not existing
            self.context_file.parent.mkdir(parents=True, exist_ok=True)
            
            # YAML format maintained
            context_dict = self.current_context.dict()
            
            with open(self.context_file, 'w', encoding='utf-8') as f:
                yaml.dump(context_dict, f, allow_unicode=True, default_flow_style=False)
            
            self.logger.info('✅ Context of the organization retained')
            
        except Exception as e:
            self.logger.error(f"❌ Mistake of keeping the context: {e}")
    
    async def _save_rules(self):
        'Save rules to file'
        try:
            # Creation of a directory if not existing
            self.rules_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Conversion to dictionaries
            rules_data = {
                "rules": [rule.dict() for rule in self.workflow_rules]
            }
            
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                yaml.dump(rules_data, f, allow_unicode=True, default_flow_style=False)
            
            self.logger.info('✅ Business rules retained')
            
        except Exception as e:
            self.logger.error(f"❌ Error in keeping the rules: {e}")
    
    async def get_hiring_process_stage(self, stage_name: str) -> Optional[Dict[str, Any]]:
        'Obtaining information on the recruitment phase'
        if not self.current_context:
            return None
        
        hiring_process = self.current_context.hiring_process
        stages = hiring_process.get("stages", [])
        
        if stage_name in stages:
            stage_index = stages.index(stage_name)
            return {
                "name": stage_name,
                "index": stage_index,
                "total_stages": len(stages),
                "next_stage": stages[stage_index + 1] if stage_index + 1 < len(stages) else None,
                "previous_stage": stages[stage_index - 1] if stage_index > 0 else None
            }
        
        return None
    
    async def get_stats(self) -> Dict[str, Any]:
        'Collection of Organization Content Manager statistics'
        return {
            "stats": self.stats,
            "context_loaded": self.current_context is not None,
            "departments_count": len(self.departments_cache),
            "roles_count": len(self.roles_cache),
            "workflow_rules_count": len(self.workflow_rules),
            "active_rules_count": len([r for r in self.workflow_rules if r.active]),
            "last_context_update": self.current_context.last_updated if self.current_context else None
        }
