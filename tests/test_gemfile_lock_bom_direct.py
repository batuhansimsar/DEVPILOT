"""Gemfile.lock BOM handling for callers providing decoded UTF-8 text."""

import unittest

from devpilot.gemfile_lock import parse_gemfile_lock


class GemfileBOMTests(unittest.TestCase):
    def test_leading_bom_does_not_hide_gem_section(self):
        content = ('\ufeffGEM\n  remote: https://user:secret@example.invalid\n'
                   '  specs:\n    Nokogiri (1.16.1)\n    Rails (7.0.0)\n'
                   '\nPLATFORMS\n  ruby\n')
        result = parse_gemfile_lock(content)
        self.assertEqual(result, ['nokogiri', 'rails'])
        self.assertNotIn('secret', str(result))

    def test_bom_inside_content_does_not_create_source_section(self):
        content = ('GEM\n  specs:\n    Rack (3.0.0)\n'
                   '\ufeffGEM\n  specs:\n    Phantom (1.0.0)\n')
        self.assertEqual(parse_gemfile_lock(content), ['rack'])


if __name__ == '__main__':
    unittest.main()
