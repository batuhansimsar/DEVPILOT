"""Regression coverage for BOM-prefixed Poetry lockfile inventories."""

import unittest

from devpilot.poetry_lock import parse_poetry_lock


class PoetryLockBomTests(unittest.TestCase):
    def test_direct_parser_accepts_leading_utf8_bom(self):
        content = ('\ufeff[[package]]\nname = "Pydantic_Core"\n'
                   'version = "2.0"\n'
                   'source = { url = "https://user:secret@example.invalid/simple" }\n'
                   '[[package]]\nname = "httpx"\nversion = "0.28"\n')
        self.assertEqual(parse_poetry_lock(content), ['httpx', 'pydantic-core'])
        self.assertNotIn('secret', str(parse_poetry_lock(content)))

    def test_bom_inside_file_is_rejected_safely(self):
        with self.assertRaisesRegex(ValueError, 'invalid poetry.lock TOML') as raised:
            parse_poetry_lock('[[package]]\nname="ok"\n\ufeff[[package]]\nname="secret"\n')
        self.assertNotIn('secret', str(raised.exception))

    def test_malformed_toml_still_redacted(self):
        with self.assertRaisesRegex(ValueError, 'invalid poetry.lock TOML') as raised:
            parse_poetry_lock('\ufeffbroken = "https://user:secret@example.invalid"\nbad = [\n')
        self.assertNotIn('secret', str(raised.exception))


if __name__ == '__main__':
    unittest.main()
