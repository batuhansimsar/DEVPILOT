"""Resource limits and privacy regressions for direct Cargo.lock parsing."""

import unittest

from devpilot.cargo_lock import MAX_CARGO_LOCK_INPUT_BYTES, parse_cargo_lock


class CargoLockResourceLimitTests(unittest.TestCase):
    def test_rejects_non_string_content_without_coercion(self):
        for content in (None, 42, b'version = 4', ['version = 4']):
            with self.subTest(content=type(content).__name__):
                with self.assertRaisesRegex(ValueError, 'safe size limit or is invalid'):
                    parse_cargo_lock(content)

    def test_rejects_oversized_ascii_input_before_toml_parsing(self):
        content = 'version = 4\n' + '#secret' * (MAX_CARGO_LOCK_INPUT_BYTES // 7)
        with self.assertRaises(ValueError) as error:
            parse_cargo_lock(content)
        self.assertNotIn('secret', str(error.exception))

    def test_rejects_multibyte_input_over_byte_limit(self):
        content = 'version = 4\n#' + 'é' * (MAX_CARGO_LOCK_INPUT_BYTES // 2)
        self.assertLess(len(content), MAX_CARGO_LOCK_INPUT_BYTES)
        with self.assertRaisesRegex(ValueError, 'safe size limit'):
            parse_cargo_lock(content)

    def test_rejects_unpaired_surrogates_without_leaking_input(self):
        with self.assertRaisesRegex(ValueError, 'valid Unicode') as error:
            parse_cargo_lock('source = "secret\ud800"')
        self.assertNotIn('secret', str(error.exception))

    def test_accepts_valid_lockfile_under_byte_limit(self):
        content = 'version = 4\n[[package]]\nname = "serde"\nversion = "1.0.0"\n'
        self.assertEqual(parse_cargo_lock(content), ['serde'])

    def test_accepts_bom_and_unicode_comments_below_limit(self):
        content = '\ufeffversion = 4\n# décor\n'
        self.assertEqual(parse_cargo_lock(content), [])


if __name__ == '__main__':
    unittest.main()
