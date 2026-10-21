"""Bound direct go.mod parser calls by UTF-8 bytes, not only characters."""
import unittest
from devpilot.go_mod import MAX_GO_MOD_INPUT_BYTES, parse_go_requirements


class GoModUTF8InputBoundsTests(unittest.TestCase):
    def test_rejects_multibyte_input_exceeding_byte_budget(self):
        # Character count remains well within 1 million, but UTF-8 bytes exceed it.
        source = 'require example.org/private v1.0.0\n' + 'é' * (MAX_GO_MOD_INPUT_BYTES // 2)
        self.assertLess(len(source), MAX_GO_MOD_INPUT_BYTES)
        with self.assertRaisesRegex(ValueError, '^go.mod input is invalid or exceeds safe size limit$') as caught:
            parse_go_requirements(source)
        self.assertNotIn('private', str(caught.exception))

    def test_rejects_unpaired_surrogate_privately(self):
        with self.assertRaisesRegex(ValueError, '^go.mod input is invalid or exceeds safe size limit$') as caught:
            parse_go_requirements('require example.org/private v1.0.0\n\ud800')
        self.assertNotIn('private', str(caught.exception))

    def test_accepts_valid_multibyte_input_inside_limit(self):
        source = 'require example.org/ok v1.2.3\n' + '// café\n'
        self.assertEqual(parse_go_requirements(source), ['example.org/ok'])


if __name__ == '__main__':
    unittest.main()
