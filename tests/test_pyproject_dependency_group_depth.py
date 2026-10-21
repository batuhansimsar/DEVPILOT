"""Regression tests for iterative PEP 735 dependency-group resolution."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class DependencyGroupDepthTests(unittest.TestCase):
    def test_deep_includes_fail_with_bounded_error(self):
        content = '[dependency-groups]\ng0 = ["pytest"]\n'
        content += ''.join(
            f'g{i} = [{{include-group = "g{i-1}"}}]\n'
            for i in range(1, 1100)
        )
        with self.assertRaisesRegex(ValueError, 'depth limit'):
            parse_pyproject_dependencies(content)

    def test_shared_and_duplicate_includes_do_not_trigger_false_cycles(self):
        content = '''[dependency-groups]
        Test_Tools = ["pytest"]
        a = [{include-group = "test-tools"}]
        b = [{include-group = "Test_Tools"}]
        ci = [{include-group = "a"}, {include-group = "b"}, {include-group = "a"}]
        '''
        self.assertEqual(parse_pyproject_dependencies(content), {
            'group:Test_Tools': ['pytest'],
            'group:a': ['pytest'],
            'group:b': ['pytest'],
            'group:ci': ['pytest'],
        })


if __name__ == '__main__':
    unittest.main()
