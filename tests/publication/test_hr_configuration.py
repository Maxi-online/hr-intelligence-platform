from pathlib import Path
import importlib.util
import sys
import unittest
import yaml
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('portfolio_hr_models',ROOT/'components/master_agent/models.py')
models=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=models
spec.loader.exec_module(models)

class OrganizationConfigurationTests(unittest.TestCase):
    def test_public_organization_has_valid_schema_and_no_customer_policy(self):
        data=yaml.safe_load((ROOT/'components/config/organization_context.yaml').read_text())
        context=models.OrganizationContext(**data)
        self.assertEqual(context.sla_requirements,{})
        self.assertEqual(data['hiring_policies']['salary_ranges'],{})
        self.assertIn('Fictional',context.industry)

    def test_public_rules_are_schema_valid_and_inactive(self):
        data=yaml.safe_load((ROOT/'components/config/workflow_rules.yaml').read_text())
        rules=[models.WorkflowRule(**row) for row in data['rules']]
        self.assertTrue(rules)
        self.assertFalse(any(rule.active for rule in rules))
