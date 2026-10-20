"""PDM dev-dependency aliases must not produce ambiguous duplicate groups."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PDMNormalizedGroupTests(unittest.TestCase):
    def test_same_group_with_different_case_and_separators_is_rejected(self):
        fixtures = (
            ('QA_Test', 'qa-test'),
            ('DOCS.tools', 'docs__tools'),
            ('Dev', 'dev'),
        )
        for first, second in fixtures:
            with self.subTest(first=first, second=second):
                source = ('[tool.pdm.dev-dependencies]\n'
                          f'"{first}" = ["pytest>=8"]\n'
                          f'"{second}" = ["ruff>=0.5"]\n')
                with self.assertRaisesRegex(ValueError, 'duplicate normalized PDM'):
                    parse_pyproject_dependencies(source)

    def test_distinct_groups_are_preserved(self):
        source = ('[tool.pdm.dev-dependencies]\n'
                  'QA_Test = ["Pytest>=8"]\n'
                  'docs = ["Sphinx>=7"]\n')
        self.assertEqual(parse_pyproject_dependencies(source), {
            'group:QA_Test': ['pytest'],
            'group:docs': ['sphinx'],
        })

    def test_invalid_pdm_group_is_rejected_without_echoing_secret(self):
        source = ('[tool.pdm.dev-dependencies]\n'
                  '"password:secret" = ["pytest"]\n')
        with self.assertRaisesRegex(ValueError, 'invalid dependency group name') as caught:
            parse_pyproject_dependencies(source)
        self.assertNotIn('secret', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
