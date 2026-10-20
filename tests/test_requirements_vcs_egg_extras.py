"""Legacy VCS egg extras identify packages without exposing private URLs."""

import unittest

from devpilot.requirements_deps import parse_requirements_dependencies


class LegacyVCSEggExtrasTests(unittest.TestCase):
    def test_legacy_eggs_with_extras_are_inventoried_without_credentials(self):
        content = (
            '-e git+https://user:secret@example.invalid/repo.git#egg=My_Pkg[cli]\n'
            'hg+https://example.invalid/repo#egg=Other.Pkg%5Bfast%2Ccli%5D\n'
            '--editable=git+ssh://git@example.invalid/repo#subdirectory=src&egg=Third-Pkg%5Bfast%2C%20crypto%5D\n'
            'git+https://example.invalid/repo#egg=NoExtras\n'
        )
        names = parse_requirements_dependencies(content)
        self.assertEqual(names, ['my-pkg', 'noextras', 'other-pkg', 'third-pkg'])
        self.assertNotIn('secret', repr(names))
        self.assertNotIn('example.invalid', repr(names))

    def test_malformed_eggs_with_extras_are_ignored(self):
        content = (
            'git+https://example.invalid/repo#egg=bad[]\n'
            'git+https://example.invalid/repo#egg=bad[extra]junk\n'
            'git+https://example.invalid/repo#egg=bad[extra,,other]\n'
            'git+https://example.invalid/repo#egg=bad%5Bextra%2Fetc%5D\n'
            'git+https://example.invalid/repo#egg=bad[extra]&egg=other\n'
            'git+https://example.invalid/repo#egg=bad[extra]&malformed\n'
            'git+https://example.invalid/repo#egg=' + 'a' * 215 + '[fast]\n'
            'git+https://example.invalid/repo#egg=bad[' + 'a' * 513 + ']\n'
        )
        self.assertEqual(parse_requirements_dependencies(content), [])


if __name__ == '__main__':
    unittest.main()
