"""Regression checks for UTF-8 BOM and shell export whitespace in .env files."""

import tempfile
import unittest
from pathlib import Path

from devpilot.envcheck import _keys, inspect_env


class EnvEncodingTests(unittest.TestCase):
    def test_bom_does_not_hide_first_local_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.env.example').write_text('API_TOKEN=placeholder\n')
            (root / '.env').write_bytes(b'\xef\xbb\xbfAPI_TOKEN=not-reported\r\n')
            result = inspect_env(root)
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['declared_count'], 1)
        self.assertNotIn('not-reported', repr(result))

    def test_bom_in_template_and_tab_separated_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.env.example').write_bytes(b'\xef\xbb\xbfexport\tAPI_TOKEN=example\n')
            (root / '.env').write_text('export API_TOKEN=hidden\n')
            self.assertEqual(inspect_env(root)['status'], 'matched')

    def test_export_prefix_is_not_removed_from_actual_key_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '.env'
            path.write_text('exported=1\nexport_KEY=2\nexport\tREAL_KEY=3\n')
            names, error = _keys(path)
        self.assertIsNone(error)
        self.assertEqual(names, {'exported', 'export_KEY', 'REAL_KEY'})


if __name__ == '__main__':
    unittest.main()
