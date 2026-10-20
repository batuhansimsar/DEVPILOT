"""Regressions for backslash-continued pip requirements."""

import unittest

from devpilot.requirements_deps import parse_requirements_dependencies

_CONT = ' ' + chr(92) + '\n'


class RequirementsContinuationTests(unittest.TestCase):
    def test_split_version_and_marker(self):
        source = ('Requests' + _CONT + '  >=2.1\n'
                  'Py_test; python_version >=' + _CONT + '  "3.10"\n')
        self.assertEqual(parse_requirements_dependencies(source),
                         ['py-test', 'requests'])

    def test_continued_hash_option(self):
        source = 'urllib3==2.2' + _CONT + '  --hash=sha256:bb22\n'
        self.assertEqual(parse_requirements_dependencies(source), ['urllib3'])

    def test_invalid_continuation_does_not_report_fake_package(self):
        source = ('fake==1.0' + _CONT + ' --trusted-host evil.test\n'
                  'valid==2\n')
        self.assertEqual(parse_requirements_dependencies(source), ['valid'])

    def test_unterminated_continuation_is_incomplete(self):
        source = 'dangling==1.0' + _CONT.rstrip('\n')
        self.assertEqual(parse_requirements_dependencies(source), [])

    def test_index_directive_continuation_remains_excluded(self):
        source = ('--extra-index-url' + _CONT
                  + '  https://user:secret@example.org/simple\n'
                  + 'requests==2\n')
        result = parse_requirements_dependencies(source)
        self.assertEqual(result, ['requests'])
        self.assertNotIn('secret', str(result))

    def test_direct_reference_comments_do_not_leak_credentials(self):
        source = ('Example @ https://user:secret@host/path#frag' + _CONT
                  + ' # note\n')
        result = parse_requirements_dependencies(source)
        self.assertEqual(result, ['example'])
        self.assertNotIn('secret', str(result))


if __name__ == '__main__':
    unittest.main()
