"""A symlinked parent must not let dependency scans escape the selected path."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.deps import scan


class DependencyScanAncestorTests(unittest.TestCase):
    def test_parent_symlink_is_rejected_before_walking_or_reading(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            nested = base / 'outside' / 'nested'
            nested.mkdir(parents=True)
            (nested / 'requirements.txt').write_text('private-package==1\n', encoding='utf-8')
            alias = base / 'alias'
            try:
                alias.symlink_to(nested.parent, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('directory symlinks unavailable')
            with patch('devpilot.deps.walk_project', side_effect=AssertionError('must not walk')):
                with self.assertRaisesRegex(ValueError, 'symbolic link') as caught:
                    scan(alias / 'nested')
            self.assertNotIn('private-package', str(caught.exception))
            self.assertNotIn(str(nested), str(caught.exception))


if __name__ == '__main__':
    unittest.main()
