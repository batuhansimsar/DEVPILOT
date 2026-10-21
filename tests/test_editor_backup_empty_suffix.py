"""Invalid empty backup suffixes must not erase tracked filenames."""

import unittest

from devpilot.editor_backups import strip_editor_backups


class EmptyBackupSuffixTests(unittest.TestCase):
    def test_empty_suffix_cannot_erase_filename(self):
        self.assertEqual(strip_editor_backups('app.env', ('',)), ('app.env', False))
        self.assertEqual(strip_editor_backups('app.env', ('', '.bak')), ('app.env', False))

    def test_valid_suffix_still_removed_when_empty_precedes_it(self):
        self.assertEqual(strip_editor_backups('app.env.bak', ('', '.bak')), ('app.env', False))

    def test_vim_detection_unchanged(self):
        self.assertEqual(strip_editor_backups('app.env.swp', ('',)), ('app.env', True))


if __name__ == '__main__':
    unittest.main()
