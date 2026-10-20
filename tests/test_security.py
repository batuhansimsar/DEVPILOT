import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.security import tracked_environment_files


class EnvironmentIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)

    def stage(self, name):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('TOP_SECRET_NEVER_OUTPUT', encoding='utf-8')
        subprocess.run(['git', '-C', str(self.root), 'add', '-f', '--', name], check=True)

    def test_warns_only_on_sensitive_paths(self):
        self.stage('.env')
        self.stage('backend/.env.production')
        self.stage('backend/.env.example')
        self.stage('.env.sample')
        self.assertEqual(tracked_environment_files(self.root), ['.env', 'backend/.env.production'])

    def test_nested_environment_templates(self):
        for name in (
            '.env.defaults',
            'backend/.env.production.example',
            'backend/.env.production.sample',
            'backend/.env.production.template',
            'backend/.env.production.dist',
            'backend/.env.production.defaults',
        ):
            self.stage(name)
        self.stage('backend/.env.production')
        self.stage('backend/.env.production.example.local')
        self.assertEqual(
            tracked_environment_files(self.root),
            ['backend/.env.production', 'backend/.env.production.example.local'],
        )

    def test_does_not_read_contents(self):
        self.stage('.env.local')
        with patch('pathlib.Path.read_text', side_effect=AssertionError('must not open .env')):
            paths = tracked_environment_files(self.root)
        self.assertEqual(paths, ['.env.local'])
        self.assertNotIn('TOP_SECRET_NEVER_OUTPUT', repr(paths))

    def test_untracked_files_are_not_findings(self):
        (self.root / '.env').write_text('SECRET')
        self.assertEqual(tracked_environment_files(self.root), [])

    def test_not_a_repository(self):
        with tempfile.TemporaryDirectory() as other:
            self.assertEqual(tracked_environment_files(Path(other)), [])

    def test_index_query_ignores_fsmonitor_and_disables_stdin(self):
        with patch('devpilot.security.subprocess.run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, b'')
            self.assertEqual(tracked_environment_files(self.root), [])
        argv = run.call_args.args[0]
        self.assertIn(['-c', 'core.fsmonitor=false'], [argv[i:i + 2] for i in range(len(argv) - 1)])
        self.assertIn('--no-optional-locks', argv)
        self.assertIs(run.call_args.kwargs['stdin'], subprocess.DEVNULL)



    def test_control_and_bidi_characters_in_tracked_paths_are_escaped(self):
        paths = b'backend/.env\x1b[2J\0backend/.env\nline\0backend/.env\xe2\x80\xae\0'
        with patch('devpilot.security.subprocess.run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, paths)
            results = tracked_environment_files(self.root)
        self.assertEqual(results, [
            r'backend/.env\u000aline', r'backend/.env\u001b[2J', r'backend/.env\u202e'
        ])
        self.assertNotIn('\x1b', ''.join(results))
        self.assertNotIn('\u202e', ''.join(results))

    def test_safe_template_filtering_precedes_escaping(self):
        paths = b'backend/.env.example\0backend/.env.secret\x1b[2J\0'
        with patch('devpilot.security.subprocess.run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, paths)
            self.assertEqual(tracked_environment_files(self.root), [r'backend/.env.secret\u001b[2J'])


if __name__ == '__main__':
    unittest.main()
