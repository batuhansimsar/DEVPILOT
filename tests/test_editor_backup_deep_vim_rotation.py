"""Vim can rotate beyond .swa to .svz through .saa; audit these backups."""

import unittest

from devpilot.editor_backups import strip_editor_backups


class VimDeepRotationTests(unittest.TestCase):
    def test_deeply_rotated_swap_files_are_normalized(self):
        for suffix in ('.swp', '.swo', '.swa', '.svz', '.svy', '.sva',
                       '.suz', '.stz', '.sbz', '.saz', '.saa'):
            with self.subTest(suffix=suffix):
                self.assertEqual(
                    strip_editor_backups('.credentials.json' + suffix, ('.bak',)),
                    ('.credentials.json', True),
                )

    def test_rotated_swap_wrapped_in_backups_is_normalized(self):
        self.assertEqual(
            strip_editor_backups('.env.production.svz.~4~.bak', ('.bak',)),
            ('.env.production', True),
        )

    def test_unrelated_extensions_not_mistaken_for_swaps(self):
        for filename in ('credentials.json.swq', 'credentials.json.swr',
                         'credentials.json.sxa', 'credentials.json.szz',
                         'credentials.json.sa0'):
            with self.subTest(filename=filename):
                self.assertEqual(strip_editor_backups(filename, ('.bak',)),
                                 (filename, False))


if __name__ == '__main__':
    unittest.main()
