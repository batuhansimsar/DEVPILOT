"""UTF-8 BOM compatibility for direct Composer inventory parser callers."""

import json
import unittest

from devpilot.composer_deps import parse_composer_dependencies


class ComposerBomTests(unittest.TestCase):
    def test_direct_parser_accepts_bom_prefixed_json(self):
        source = '\ufeff' + json.dumps({'require': {'php': '^8.2', 'psr/log': '^3.0'}})
        self.assertEqual(parse_composer_dependencies(source),
                         {'require': ['php', 'psr/log']})

    def test_only_bom_does_not_hide_malformed_json(self):
        with self.assertRaises(json.JSONDecodeError):
            parse_composer_dependencies('\ufeff')

    def test_embedded_bom_is_rejected(self):
        with self.assertRaises(json.JSONDecodeError):
            parse_composer_dependencies('{"require": {}}\ufeff')

    def test_normal_json_and_duplicate_key_rejection_unchanged(self):
        self.assertEqual(parse_composer_dependencies('{}'), {})
        with self.assertRaisesRegex(ValueError, 'duplicate object keys'):
            parse_composer_dependencies('{"require":{}, "require":{}}')


if __name__ == '__main__':
    unittest.main()
