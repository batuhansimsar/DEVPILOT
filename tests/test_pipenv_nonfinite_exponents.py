"""Reject JSON numeric overflow in Pipenv lockfiles without revealing metadata."""

import unittest

from devpilot.pipenv_deps import parse_pipfile_lock


class PipenvNonFiniteExponentTests(unittest.TestCase):
    def test_overflow_in_metadata_or_package_values_is_rejected(self):
        for content in (
            '{"_meta":{"secret":1e999},"default":{"requests":{}}}',
            '{"default":{"requests":{"version":-1e999}}}',
            '{"develop":{"pytest":{"value":1E999}}}',
        ):
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, "finite JSON numbers") as captured:
                    parse_pipfile_lock(content)
                self.assertNotIn("secret", str(captured.exception))
                self.assertNotIn("requests", str(captured.exception))

    def test_finite_exponents_remain_supported(self):
        self.assertEqual(
            parse_pipfile_lock('{"_meta":{"value":1e2},"default":{"requests":{"size":-1.25e-2}}}'),
            {"default": ["requests"]},
        )


if __name__ == "__main__":
    unittest.main()
