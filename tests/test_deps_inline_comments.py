"""Whitespace-prefixed pip inline comments must not hide dependencies."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class RequirementsInlineCommentsTests(unittest.TestCase):
    def test_bare_requirements_and_extras_with_inline_comments(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, 'requirements.txt').write_text(
                'requests # production dependency\n'
                'Fancy_Pkg[http]   # with extras\n'
                'pytest>=8 # pinned by toolchain\n'
                'pydantic; python_version >= "3.10" # marker\n', encoding='utf-8'
            )
            result = scan(temp)
            self.assertEqual(result['manifests'][0]['groups']['requirements'],
                             ['fancy-pkg', 'pydantic', 'pytest', 'requests'])
            self.assertEqual(result['totals'], {'Python': 4})

    def test_url_fragment_not_treated_as_comment_and_no_credentials_exposed(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, 'requirements.txt').write_text(
                'example-pkg @ https://user:secret@example.org/archive.whl#sha256=abc # note\n'
                'requests#not-an-inline-comment\n'
                '--extra-index-url https://user:token@example.org/simple\n'
                '# full-line comment\n', encoding='utf-8'
            )
            result = scan(temp)
            self.assertEqual(result['manifests'][0]['groups']['requirements'], ['example-pkg'])
            serialized = json.dumps(result)
            self.assertNotIn('secret', serialized)
            self.assertNotIn('token', serialized)
            self.assertNotIn('sha256', serialized)


if __name__ == '__main__':
    unittest.main()
