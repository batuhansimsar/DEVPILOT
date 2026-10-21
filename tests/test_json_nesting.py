"""The nesting budget must not depend on CPython's JSON decoder stack."""

import json
import unittest
from unittest.mock import patch

from devpilot.composer_deps import parse_composer_dependencies
from devpilot.composer_lock import parse_composer_lock
from devpilot.json_nesting import MAX_JSON_DEPTH, JSONNestingError, validate_json_nesting


class JSONNestingTests(unittest.TestCase):
    def test_exact_limit_is_allowed_and_one_more_level_is_rejected(self):
        validate_json_nesting('[' * MAX_JSON_DEPTH + '0' + ']' * MAX_JSON_DEPTH)
        with self.assertRaises(JSONNestingError):
            validate_json_nesting('[' * (MAX_JSON_DEPTH + 1) + '0' + ']' * (MAX_JSON_DEPTH + 1))

    def test_quoted_brackets_escaped_quotes_and_backslashes_are_not_structure(self):
        value = '[{"\\' * (MAX_JSON_DEPTH + 1)
        validate_json_nesting(json.dumps({'text': value}))
        validate_json_nesting(json.dumps(value) + ' ')

    def test_mixed_objects_and_arrays_share_the_budget(self):
        content = '{"nested":' * 64 + '[' * 65 + '0' + ']' * 65 + '}' * 64
        with self.assertRaises(JSONNestingError):
            validate_json_nesting(content)

    def test_composer_rejects_deep_metadata_before_invoking_decoder(self):
        content = '{"extra":' + '[' * MAX_JSON_DEPTH + '0' + ']' * MAX_JSON_DEPTH + '}'
        for parser in (parse_composer_dependencies, parse_composer_lock):
            with self.subTest(parser=parser.__name__), patch('json.loads') as loads:
                with self.assertRaises(ValueError):
                    parser(content)
                loads.assert_not_called()


if __name__ == '__main__':
    unittest.main()
