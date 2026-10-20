"""Regression coverage for malformed PEP 508 dependency tails."""

import json
import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PyprojectRequirementSuffixTests(unittest.TestCase):
    def test_rejects_incomplete_or_unexpected_suffixes(self):
        for requirement in (
            'Flask unexpected', 'Requests @', 'requests >', 'demo[',
            'demo[good,,bad]', 'demo>=1 nonsense', 'demo;',
            'demo >= 1,', 'demo (>=1', 'demo >=1)',
            'demo @ https://example.invalid/file ;',
        ):
            with self.subTest(requirement=requirement):
                content = '[project]\ndependencies = [' + json.dumps(requirement) + ']\n'
                with self.assertRaisesRegex(ValueError, 'invalid requirement') as raised:
                    parse_pyproject_dependencies(content)
                self.assertNotIn(requirement, str(raised.exception))

    def test_invalid_requirement_is_rejected_in_all_list_formats(self):
        for content in (
            '[project.optional-dependencies]\nqa = ["Flask unexpected"]\n',
            '[dependency-groups]\nqa = ["Flask unexpected"]\n',
            '[tool.pdm.dev-dependencies]\nqa = ["Flask unexpected"]\n',
        ):
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, 'invalid requirement'):
                    parse_pyproject_dependencies(content)

    def test_accepts_valid_versions_extras_urls_and_markers(self):
        requirements = (
            'Requests[security]>=2', 'My_Pkg @ https://user:secret@example.invalid/a;b',
            'Flask ; python_version >= "3.10"', 'requests (>=2, <4)',
            'Ruff>=0.1,!=0.2',
            'demo @ git+https://example.invalid/demo.git ; python_version >= "3.11"',
        )
        content = '[project]\ndependencies = ' + json.dumps(requirements) + '\n'
        groups = parse_pyproject_dependencies(content)
        self.assertEqual(groups, {'dependencies': ['demo', 'flask', 'my-pkg', 'requests', 'ruff']})
        self.assertNotIn('secret', str(groups))


if __name__ == '__main__':
    unittest.main()
