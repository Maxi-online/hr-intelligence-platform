"""Display-name localization must not change agent configuration selection."""
import ast
from pathlib import Path
import re
from typing import Any
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]

class AgentLanguageContracts(unittest.TestCase):
    def test_configuration_uses_class_identity_for_every_agent(self):
        for component in ('candidate_ranking', 'recruitment_runtime'):
            directory = ROOT / 'components' / component / 'ai_analysis'
            source = (directory / 'agents.py').read_text(encoding='utf-8')
            tree = ast.parse(source)
            base = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BaseAgent')
            method = next(n for n in base.body if isinstance(n, ast.FunctionDef) and n.name == '_get_agent_config')
            namespace = {'re': re, 'Any': Any}
            exec(compile(ast.Module(body=[method], type_ignores=[]), str(directory / 'agents.py'), 'exec'), namespace)
            config = yaml.safe_load((directory / 'agent_configs.yaml').read_text(encoding='utf-8'))
            for cls in tree.body:
                if not isinstance(cls, ast.ClassDef) or cls.name == 'BaseAgent':
                    continue
                key = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.name).lower()
                self.assertIn(key, config['agents'])
                instance = type(cls.name, (), {})()
                instance.name = 'A localized display label'
                instance.agent_configs = {'agents': {key: {'translation_probe': 73}}}
                with self.subTest(component=component, agent=cls.name):
                    self.assertEqual(namespace['_get_agent_config'](instance, 'translation_probe'), 73)

if __name__ == '__main__':
    unittest.main()
