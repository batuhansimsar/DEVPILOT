"""Vim rotates beyond .swa when more swap-file names are occupied."""

import unittest

from devpilot.editor_backups import strip_editor_backups


class VimExtendedSwapRotationTests(unittest.TestCase):
    def test_every_rotated_suffix_keeps_swap_flag(self):
        for group in 'abcdefghijklmnopqrstuv':
            for suffix in 'abcdefghijklmnopqrstuvwxyz':
                name = f'.credentials.json.s{group}{suffix}'
                with self.subTest(name=name):
                    self.assertEqual(strip_editor_backups(name, ()),
                                     ('.credentials.json', True))

    def test_original_sw_rotation_remains_bounded(self):
        for final in 'abcdefghijklmnop':
            self.assertEqual(strip_editor_backups(f'..pgpass.sw{final}', ()),
                             ('..pgpass', True))
        for final in 'qrstuvwxyz':
            self.assertEqual(strip_editor_backups(f'..pgpass.sw{final}', ()),
                             (f'..pgpass.sw{final}', False))

    def test_nested_backups_and_safe_write_are_unwrapped(self):
        cases = {
            '..pgpass.svz.bak': ('..pgpass', True),
            '.credentials.json.saa.___jb_tmp___': ('.credentials.json', True),
            '.env.production.suy.old': ('.env.production', True),
            'README.md.svy': ('README.md', True),
            '.svz': ('.svz', False),
            '.env.production.swq.bak': ('.env.production.swq', False),
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(strip_editor_backups(name, ('.bak', '.old')), expected)


if __name__ == '__main__':
    unittest.main()
