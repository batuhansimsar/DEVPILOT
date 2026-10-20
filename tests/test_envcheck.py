import tempfile
import unittest
from pathlib import Path

from devpilot.envcheck import MAX_ENV_BYTES, inspect_env


class EnvCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, text):
        (self.root / name).write_text(text, encoding='utf-8')

    def test_missing_keys_are_sorted_and_values_never_exposed(self):
        self.write('.env.example', '# ignored=bad\nexport TOKEN=top-secret\nDB_URL=postgres://example\n')
        self.write('.env', 'TOKEN=live-secret\n')
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'missing_keys')
        self.assertEqual(result['missing_keys'], ['DB_URL'])
        self.assertNotIn('secret', str(result))
        self.assertNotIn('postgres://', str(result))

    def test_absent_local_is_informational(self):
        self.write('.env.sample', 'API_KEY=value\n')
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'local_absent')
        self.assertNotIn('missing_keys', result)

    def test_template_size_limit(self):
        (self.root / '.env.example').write_bytes(b'x' * (MAX_ENV_BYTES + 1))
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'unreadable_template')
        self.assertIn('limit', result['detail'])

    def test_symlinks_not_read(self):
        other = Path(self.tmp.name) / 'value'
        other.write_text('SECRET=private', encoding='utf-8')
        try:
            (self.root / '.env.example').symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks not available')
        self.assertEqual(inspect_env(self.root)['status'], 'unreadable_template')

    def test_empty_or_missing_template(self):
        self.assertEqual(inspect_env(self.root)['status'], 'no_template')
        self.write('.env.example', '# comment only\n')
        self.write('.env', 'IGNORED=yes\n')
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['expected_count'], 0)


if __name__ == '__main__':
    unittest.main()
