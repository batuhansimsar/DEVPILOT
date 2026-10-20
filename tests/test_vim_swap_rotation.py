"""Vim's successive swap names remain recognizable in credential audits."""

import unittest

from devpilot.editor_backups import strip_editor_backups
from devpilot.secret_audit import classify
from devpilot.audit import _potential_secret

_BACKUP_SUFFIXES = ('.bak', '.backup', '.old', '.orig', '.save', '~', '.tmp', '.swp', '.swo', '.swn')


class VimSwapRotationTests(unittest.TestCase):
    def test_all_vim_swap_letters_are_normalized(self):
        for suffix in 'abcdefghijklmnop':
            with self.subTest(suffix=suffix):
                self.assertEqual(strip_editor_backups('.credentials.json.sw' + suffix, _BACKUP_SUFFIXES),
                                 ('.credentials.json', True))

    def test_new_rotation_suffixes_are_audited_by_both_tools(self):
        for path in ('.credentials.json.swm', '..pgpass.swl',
                     '.auth.json.swk.bak', '.config/pip/.pip.conf.swa'):
            with self.subTest(path=path):
                self.assertIsNotNone(classify(path))
                self.assertTrue(_potential_secret(path))

    def test_templates_and_unrelated_suffixes_remain_safe(self):
        for path in ('docs/.credentials.example.json.swm', 'docs/README.md.swl',
                     'docs/.env.example.swa', '.credentials.json.swq'):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))

    def test_deep_backup_chains(self):
        name = '.credentials.json.swm.bak.old'
        self.assertEqual(strip_editor_backups(name, _BACKUP_SUFFIXES), ('.credentials.json', True))


if __name__ == '__main__':
    unittest.main()
