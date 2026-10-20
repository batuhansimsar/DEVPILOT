"""PEP 735 normalized group references and safe inclusion regression coverage."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PEP735NormalizationTests(unittest.TestCase):
    def test_case_and_separator_normalized_includes(self):
        result = parse_pyproject_dependencies('''[dependency-groups]
Dev_Test = ["pytest>=8", "private_pkg @ https://u:secret@example.invalid/file"]
ci = [{include-group = "DEV.TEST"}, "ruff>=0.5", {include-group = "dev-test"}]
''')
        self.assertEqual(result, {
            'group:ci': ['private-pkg', 'pytest', 'ruff'],
            'group:dev-test': ['private-pkg', 'pytest'],
        })
        self.assertNotIn('secret', str(result))

    def test_reject_equivalent_duplicate_names(self):
        with self.assertRaisesRegex(ValueError, 'normaliz'):
            parse_pyproject_dependencies('''[dependency-groups]
Dev_Test = []
"dev.test" = []
''')

    def test_reject_unknown_or_cyclic_references(self):
        for content in (
            '[dependency-groups]\ndev = [{include-group = "missing"}]\n',
            '[dependency-groups]\ndev = [{include-group = "DEV"}]\n',
            '[dependency-groups]\na = [{include-group = "b"}]\nb = [{include-group = "a"}]\n',
        ):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_pyproject_dependencies(content)

    def test_bounded_include_depth(self):
        lines = ['[dependency-groups]']
        for index in range(70):
            lines.append(f'g{index} = [{{include-group = "g{index + 1}"}}]')
        lines.append('g70 = ["pytest"]')
        with self.assertRaisesRegex(ValueError, 'too deep'):
            parse_pyproject_dependencies('\n'.join(lines))

    def test_invalid_group_names_are_not_echoed(self):
        with self.assertRaises(ValueError) as context:
            parse_pyproject_dependencies('[dependency-groups]\n"bad secret name" = ["pytest"]\n')
        self.assertNotIn('secret', str(context.exception))


if __name__ == '__main__':
    unittest.main()
