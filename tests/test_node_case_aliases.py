"""Reject ambiguous npm dependency names that differ only by casing."""

import unittest

from devpilot.node_deps import parse_node_dependency_groups


class NodeCaseAliasTests(unittest.TestCase):
    def test_case_aliases_rejected_in_every_group(self):
        for group in ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'):
            with self.subTest(group=group):
                with self.assertRaisesRegex(ValueError, 'duplicate case-insensitive') as error:
                    parse_node_dependency_groups({group: {'React': '^18', 'react': '^19'}})
                self.assertNotIn('React', str(error.exception))
                self.assertNotIn('^18', str(error.exception))

    def test_scoped_names_cannot_bypass_case_collision_detection(self):
        with self.assertRaisesRegex(ValueError, 'duplicate case-insensitive'):
            parse_node_dependency_groups({'dependencies': {
                '@Team/Tool': '1', '@team/tool': '2',
            }})

    def test_group_boundaries_remain_independent(self):
        self.assertEqual(parse_node_dependency_groups({
            'dependencies': {'React': '^18'},
            'devDependencies': {'react': '^19'},
        }), {'dependencies': ['React'], 'devDependencies': ['react']})

    def test_distinct_packages_are_unaffected(self):
        self.assertEqual(parse_node_dependency_groups({
            'dependencies': {'@team/tool': '1', '@team/utils': '2', 'react-dom': '3'},
        }), {'dependencies': ['@team/tool', '@team/utils', 'react-dom']})


if __name__ == '__main__':
    unittest.main()
