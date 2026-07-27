import unittest
import os
import shutil
from swe_agent.core.sandbox import LocalSandbox
from swe_agent.skills.markdown_skill import MarkdownSkill
from swe_agent.skills.testbed.validator import SkillValidator

class TestSkillTestbed(unittest.TestCase):
    def setUp(self):
        self.workspace = "./test_testbed_workspace"
        os.makedirs(self.workspace, exist_ok=True)
        self.sandbox = LocalSandbox(self.workspace)
        self.validator = SkillValidator(self.sandbox)
        
        # Write a dummy SKILL.md file inside the workspace
        self.md_content = """---
name: test-markdown-skill
description: A dynamically loaded markdown skill to test.
version: 1.2.3
category: testing
level: atomic
tags: [unit-test, dynamic]
input:
  type: object
  required: [target]
  properties:
    target:
      type: string
      description: The value to write.
constraints:
  host:
    os: [windows, linux]
---
Test instructions here.
"""
        self.skill_file = os.path.join(self.workspace, "SKILL.md")
        with open(self.skill_file, "w", encoding="utf-8") as f:
            f.write(self.md_content)

    def tearDown(self):
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

    def test_markdown_skill_loading(self):
        """
        Verify that MarkdownSkill parses YAML frontmatter and builds Pydantic args_schema dynamically.
        """
        # Inject empty tools list and brain=None (under DIP)
        skill = MarkdownSkill(self.skill_file, brain=None, tools=[])

        # Assert frontmatter parsing
        self.assertEqual(skill.name, "test-markdown-skill")
        self.assertEqual(skill.version, "1.2.3")
        self.assertEqual(skill.category, "testing")
        self.assertEqual(skill.level, "atomic")
        self.assertIn("unit-test", skill.tags)
        
        # Assert dynamic schema generation
        self.assertTrue(hasattr(skill, "args_schema"))
        schema = skill.args_schema.model_json_schema()
        self.assertIn("target", schema["properties"])
        self.assertIn("target", schema["required"])

    def test_markdown_skill_requires_brain(self):
        """
        Verify that execution fails with ValueError if dependencies (brain) are missing,
        satisfying the 'no mock code allowed' rule.
        """
        skill = MarkdownSkill(self.skill_file, brain=None, tools=[])
        with self.assertRaises(ValueError):
            skill.execute(self.sandbox, target="hello")

if __name__ == "__main__":
    unittest.main()
