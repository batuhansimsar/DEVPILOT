"""Regression tests for pip's escaped line continuation syntax."""

import unittest

from devpilot.requirements_deps import parse_requirements_dependencies


class RequirementsContinuationTests(unittest.TestCase):
    def test_split_version_extras_and_markers(self):
        content = ('Fancy_Pkg[fast] \\\n'
                   '  >=2.0; python_version >= "3.10"\n'
                   'requests \\\n'
                   '  ==2.31\n')
        self.assertEqual(parse_requirements_dependencies(content),
                         ['fancy-pkg', 'requests'])

    def test_split_direct_reference_preserves_name_only(self):
        content = ('Private_Pkg @ \\\n'
                   '  https://user:super-secret@example.invalid/archive.whl#sha256=abc\n')
        names = parse_requirements_dependencies(content)
        self.assertEqual(names, ['private-pkg'])
        self.assertNotIn('super-secret', repr(names))

    def test_multiline_hash_options(self):
        content = ('urllib3==2.0 \\\n'
                   '  --hash=sha256:aabb \\\n'
                   '  --hash=sha512:ffee\n')
        self.assertEqual(parse_requirements_dependencies(content), ['urllib3'])

    def test_continued_directives_only_inventory_explicit_vcs_egg(self):
        content = ('--index-url \\\n'
                   '  https://user:secret@example.invalid/simple\n'
                   '-r \\\n'
                   '  other-requirements.txt\n'
                   '-e \\\n'
                   '  git+https://example.invalid/repo#egg=package\n')
        self.assertEqual(parse_requirements_dependencies(content), ['package'])

    def test_dangling_continuation_is_not_a_valid_requirement(self):
        self.assertEqual(parse_requirements_dependencies('requests==2 \\\n'), [])

    def test_invalid_orphan_hash_does_not_hide_next_requirement(self):
        text = '--hash=sha256:abcd\nflask==3.0\n'
        self.assertEqual(parse_requirements_dependencies(text), ['flask'])

    def test_existing_noncontinued_requirements_remain_supported(self):
        content = ('requests==2 # comment\n'
                   'Flask>=3\n'
                   'broken==\n')
        self.assertEqual(parse_requirements_dependencies(content), ['flask', 'requests'])


if __name__ == '__main__':
    unittest.main()
