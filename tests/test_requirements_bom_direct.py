"""Direct parser regression tests for UTF-8 BOM in requirements files."""

import unittest

from devpilot.requirements_deps import parse_requirements_dependencies


class RequirementsDirectBOMTests(unittest.TestCase):
    def test_first_requirement_not_lost_after_utf8_bom(self):
        content = '\ufeffRequests>=2\nFlask==3\n'
        self.assertEqual(parse_requirements_dependencies(content), ['flask', 'requests'])

    def test_bom_before_continued_first_requirement(self):
        content = '\ufeffurllib3==2.0 \\\n  --hash=sha256:abcd\n'
        self.assertEqual(parse_requirements_dependencies(content), ['urllib3'])

    def test_embedded_and_repeated_boms_are_not_silently_discarded(self):
        content = 'requests>=2\n\ufeffprivate==1\n'
        self.assertEqual(parse_requirements_dependencies(content), ['requests'])
        self.assertEqual(parse_requirements_dependencies('\ufeff\ufeffprivate==1\n'), [])


if __name__ == '__main__':
    unittest.main()
