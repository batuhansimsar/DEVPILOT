"""PEP 621 inventory regression tests."""
import tempfile
import unittest
from pathlib import Path
from devpilot.pyproject_deps import parse_pyproject_dependencies
from devpilot.deps import scan


class PyprojectDependenciesTests(unittest.TestCase):
    def test_dependency_groups_redact_versions_and_urls(self):
        value = """[project]
name = "demo"
dependencies = ["Requests[security]>=2", "my_pkg @ https://user:token@example.invalid/file", "requests==3"]
[project.optional-dependencies]
dev = ["pytest>=8", "Black==24"]
[build-system]
requires = ["setuptools>=65"]
"""
        groups = parse_pyproject_dependencies(value)
        self.assertEqual(groups, {'dependencies': ['my-pkg', 'requests'], 'optional:dev': ['black', 'pytest']})
        self.assertNotIn('token', str(groups))
        self.assertNotIn('setuptools', str(groups))

    def test_tool_only_and_empty_project(self):
        self.assertEqual(parse_pyproject_dependencies('[tool.ruff]\nline-length = 99\n'), {})
        self.assertEqual(parse_pyproject_dependencies('[project]\nname = "demo"\n'), {})

    def test_invalid_values_do_not_echo_private_url(self):
        for value in (
            '[project]\ndependencies = "bad"\n',
            '[project]\ndependencies = [42]\n',
            '[project]\ndependencies = ["--index-url https://user:password@example.invalid"]\n',
            '[project]\noptional-dependencies = "bad"\n',
            '[project.optional-dependencies]\ndev = [42]\n',
            '[project\n',
        ):
            with self.subTest(value=value), self.assertRaises(ValueError) as error:
                parse_pyproject_dependencies(value)
            self.assertNotIn('password', str(error.exception))

    def test_scan_integration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pyproject.toml').write_text(
                '[project]\nname="demo"\ndependencies=["httpx>=0.27", "private_pkg @ https://user:secret@example.invalid/wheel"]\n'
                '[project.optional-dependencies]\ntest=["pytest>=8"]\n', encoding='utf-8')
            report = scan(root)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['totals'], {'Python': 3})
        self.assertEqual(report['manifests'][0]['groups'], {
            'dependencies': ['httpx', 'private-pkg'], 'optional:test': ['pytest']})
        self.assertNotIn('secret', str(report))


if __name__ == '__main__':
    unittest.main()
