"""The dependency inventory must report truncation only when it skipped a manifest."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.deps import main, scan


class DependencyManifestLimitTests(unittest.TestCase):
    def _root_with_manifests(self, count: int, root: Path) -> None:
        for index in range(count):
            module = root / f'module-{index:02d}'
            module.mkdir()
            (module / 'go.mod').write_text(
                f'module example.org/mod{index}\nrequire example.org/dep{index} v1.0.0\n',
                encoding='utf-8',
            )

    def test_exact_limit_is_complete_and_cli_succeeds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._root_with_manifests(2, root)
            with patch('devpilot.deps.MAX_FILES', 2):
                report = scan(root)
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(['--path', str(root), '--json'])
            self.assertEqual(len(report['manifests']), 2)
            self.assertEqual(report['totals'], {'Go': 2})
            self.assertEqual(report['warnings'], [])
            self.assertFalse(report['truncated'])
            self.assertEqual(code, 0)

    def test_limit_plus_one_is_incomplete_and_cli_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._root_with_manifests(3, root)
            with patch('devpilot.deps.MAX_FILES', 2):
                report = scan(root)
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(['--path', str(root), '--json'])
            self.assertEqual(len(report['manifests']), 2)
            self.assertEqual(report['totals'], {'Go': 2})
            self.assertTrue(report['truncated'])
            self.assertEqual(report['warnings'], ['Scan limited to 2 manifests'])
            self.assertEqual(code, 1)


if __name__ == '__main__':
    unittest.main()
