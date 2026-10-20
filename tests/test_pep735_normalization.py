"""PEP 735 normalized group references and safe inclusion regression coverage."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PEP735NormalizationTests(unittest.TestCase):
    def test_case_and_separator_normalized_includes(self):
        result = parse_pyproject_dependencies('''[dependency-groups]
Dev_Test = ["pytest>=8", "private_pkg @ https://u:secret@example.invalid/file"]
ci = [{include-group = "DEV.TEST"}, "ruff>=0.5", {include-group = "dev-test"}]
''')
        self.assertEqual({key.lower().replace('_', '-').replace('.', '-'): value
                          for key, value in result.items()}, {
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
        with self.assertRaisesRegex(ValueError, 'depth|too deep'):
            parse_pyproject_dependencies('\n'.join(lines))

    def test_include_depth_limit_is_order_independent(self):
        def lockfile(depth: int, reverse: bool) -> str:
            indices = list(range(depth + 1))
            if reverse:
                indices.reverse()
            lines = ['[dependency-groups]']
            for number in indices:
                if number == depth:
                    lines.append(f'g{number} = ["pytest"]')
                else:
                    lines.append(f'g{number} = [{{include-group = "g{number + 1}"}}]')
            return '\n'.join(lines)

        for reverse in (False, True):
            with self.subTest(reverse=reverse, depth=64):
                groups = parse_pyproject_dependencies(lockfile(64, reverse))
                self.assertEqual(groups['group:g0'], ['pytest'])
            with self.subTest(reverse=reverse, depth=65):
                with self.assertRaisesRegex(ValueError, 'depth'):
                    parse_pyproject_dependencies(lockfile(65, reverse))

    def test_invalid_group_names_are_not_echoed(self):
        with self.assertRaises(ValueError) as context:
            parse_pyproject_dependencies('[dependency-groups]\n"bad secret name" = ["pytest"]\n')
        self.assertNotIn('secret', str(context.exception))


if __name__ == '__main__':
    unittest.main()
