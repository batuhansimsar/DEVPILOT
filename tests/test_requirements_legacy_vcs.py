"""Legacy pip #egg= VCS references are named dependencies, not URL output."""

import unittest
from devpilot.requirements_deps import parse_requirements_dependencies


class LegacyVCSRequirementsTests(unittest.TestCase):
    def test_editable_and_noneditable_vcs_are_inventoried(self):
        text = (
            '-e git+https://user:secret@example.invalid/org/repo.git#egg=My_Pkg\n'
            '--editable=git+ssh://git@example.invalid/org/repo.git#subdirectory=src%2Flib&egg=Other.Pkg\n'
            'hg+https://example.invalid/lib#egg=Third-Pkg\n'
            'requests==2.3\n'
        )
        self.assertEqual(parse_requirements_dependencies(text),
                         ['my-pkg', 'other-pkg', 'requests', 'third-pkg'])
        self.assertNotIn('secret', repr(parse_requirements_dependencies(text)))

    def test_invalid_ambiguous_or_anonymous_vcs_is_skipped(self):
        text = (
            '-e git+https://example.invalid/org/repo.git\n'
            'git+https://example.invalid/org/repo.git#egg=bad/name\n'
            'git+https://example.invalid/org/repo.git#egg=first&egg=second\n'
            'git+https://example.invalid/org/repo.git#egg=\n'
            'git+https://example.invalid/org/repo.git#egg=foo&malformed\n'
            'git+https://example.invalid/org/repo.git#egg=foo#extra\n'
            'git+ftp://example.invalid/org/repo.git#egg=foo\n'
            'git+https://example.invalid/org/repo.git#egg=foo%2Fbar\n'
            'git+https://example.invalid/org/repo.git#egg=too-long-' + 'a'*215 + '\n'
            'git+https://example.invalid/org/repo.git#egg=foo&' + '&'.join('p=x' for _ in range(17)) + '\n'
        )
        self.assertEqual(parse_requirements_dependencies(text), [])

    def test_compatibility_with_existing_requirements_and_pep508(self):
        text = (
            'Example-Pkg @ https://user:secret@example.org/a.whl#sha256=abc\n'
            'urllib3==2.2 \
    --hash=sha256:bb22\n'
            '-e named_pkg @ git+https://example.org/repo.git\n'
            '--index-url https://user:secret@example.org/simple\n'
        )
        self.assertEqual(parse_requirements_dependencies(text), ['example-pkg', 'named-pkg', 'urllib3'])


if __name__ == '__main__':
    unittest.main()
