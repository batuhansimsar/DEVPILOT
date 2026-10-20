"""Regression coverage for untrusted packageManager metadata."""

import tempfile
import unittest
from pathlib import Path

from devpilot.node import package_manager


class PackageManagerDeclarationValidationTests(unittest.TestCase):
    def test_malformed_versions_cannot_override_detected_lockfile(self):
        malformed = (
            'pnpm@9.0.0\n',
            'pnpm@9.0.0\t',
            'pnpm@9.0.0\r',
            'pnpm@9.0.0\x1b',
            'pnpm@9.0.0 ',
            'pnpm@9.0.0\u00a0',
            'pnpm@9.0.0\u200b',
            'pnpm@9.0.0\u202e',
            'pnpm@' + '1' * 129,
        )
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'yarn.lock').touch()
            for declaration in malformed:
                with self.subTest(declaration=declaration):
                    self.assertEqual(
                        package_manager(root, {'packageManager': declaration}),
                        ('yarn', ['yarn.lock'], None),
                    )

    def test_corepack_integrity_suffix_is_supported(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                package_manager(Path(d), {'packageManager': 'pnpm@9.0.0+sha512.abc123'}),
                ('pnpm', [], 'pnpm'),
            )


if __name__ == '__main__':
    unittest.main()
