"""Only explicitly named editable direct references can enter the inventory."""
import unittest

from devpilot.requirements_deps import parse_requirements_dependencies


class EditableRequirementsTests(unittest.TestCase):
    def test_named_editable_vcs_urls_are_inventoried_without_credentials(self):
        content = ('-e Private_Pkg @ git+https://user:secret@example.invalid/repo.git\n'
                   '--editable "Other.Pkg[extra] @ git+ssh://git@example.invalid/repo.git"\n'
                   '--editable=\'Third_pkg @ https://user:password@example.invalid/pkg.whl\'\n'
                   'requests>=2\n')
        names = parse_requirements_dependencies(content)
        self.assertEqual(names, ['other-pkg', 'private-pkg', 'requests', 'third-pkg'])
        self.assertNotIn('secret', repr(names))
        self.assertNotIn('password', repr(names))

    def test_anonymous_or_path_editables_are_not_inventoried(self):
        content = ('-e .\n-e ../package\n-e git+https://host/repo.git#egg=Pkg\n'
                   '--editable=git+https://host/repo.git\n-e requests==2\n'
                   '-e invalid @\n--index-url https://user:secret@example.invalid/simple\n')
        self.assertEqual(parse_requirements_dependencies(content), [])

    def test_continued_named_editable_and_inline_comment(self):
        content = ('-e "Demo_Pkg @ \\\n'
                   '  git+https://user:secret@example.invalid/repo.git" # note\n'
                   'valid==2\n')
        self.assertEqual(parse_requirements_dependencies(content), ['demo-pkg', 'valid'])

    def test_existing_hashes_and_dangling_continuation(self):
        self.assertEqual(parse_requirements_dependencies('Requests==2 --hash sha256:aabb\n'), ['requests'])
        self.assertEqual(parse_requirements_dependencies('dangling==1 \\\n'), [])


if __name__ == '__main__':
    unittest.main()
