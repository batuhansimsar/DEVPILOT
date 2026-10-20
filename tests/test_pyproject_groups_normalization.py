"""PEP 735 group aliases must resolve canonically and remain bounded."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class DependencyGroupNormalizationTests(unittest.TestCase):
    def test_include_normalizes_case_and_punctuation(self):
        pyproject = '''[dependency-groups]
            Type_Check = ["mypy>=1", "types-requests"]
            dev = [{include-group = "type-check"}, "pytest>=8"]
        '''
        result = parse_pyproject_dependencies(pyproject)
        self.assertEqual(result['group:Type_Check'], ['mypy', 'types-requests'])
        self.assertEqual(result['group:dev'], ['mypy', 'pytest', 'types-requests'])

    def test_duplicate_normalized_names_are_rejected(self):
        pyproject = '''[dependency-groups]
            Type_Check = ["mypy"]
            type-check = ["pytest"]
        '''
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            parse_pyproject_dependencies(pyproject)

    def test_cycle_after_normalization_is_rejected(self):
        pyproject = '''[dependency-groups]
            dev = [{include-group="TEST"}]
            Test = [{include-group="Dev"}]
        '''
        with self.assertRaisesRegex(ValueError, 'cycl'):
            parse_pyproject_dependencies(pyproject)

    def test_deep_chain_fails_with_bounded_error(self):
        definitions = [f'g{i} = [{{include-group="g{i+1}"}}]' for i in range(70)]
        definitions.append('g70 = ["pytest"]')
        with self.assertRaisesRegex(ValueError, 'depth limit'):
            parse_pyproject_dependencies('[dependency-groups]\n' + '\n'.join(definitions))


if __name__ == '__main__':
    unittest.main()
