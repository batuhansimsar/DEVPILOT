"""Scala sbt projects must be discoverable and selectable without executing sbt."""

import tempfile
import unittest
from pathlib import Path

from devpilot.cli import build_parser
from devpilot.core import test_commands
from devpilot.test_selection import ECOSYSTEMS, select_test_commands
from devpilot.workspaces import discover_workspaces


class ScalaWorkspaceSelectionTests(unittest.TestCase):
    def test_nested_and_root_sbt_builds_are_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.sbt').write_text('name := "root"\n', encoding='utf-8')
            nested = root / 'services' / 'api'
            nested.mkdir(parents=True)
            (nested / 'build.sbt').write_text('name := "api"\n', encoding='utf-8')

            report = discover_workspaces(root)
            entries = {workspace['path']: workspace for workspace in report['workspaces']}
            self.assertFalse(report['truncated'])
            self.assertEqual(report['workspace_count'], 2)
            for path in ('.', 'services/api'):
                with self.subTest(path=path):
                    self.assertIn('Scala', entries[path]['ecosystems'])
                    self.assertIn({'file': 'build.sbt', 'ecosystem': 'Scala'}, entries[path]['manifests'])

    def test_cli_accepts_scala_and_filters_sbt_command(self):
        args = build_parser().parse_args(['test', '--ecosystem', 'scala'])
        self.assertEqual(args.ecosystem, 'scala')
        self.assertEqual(ECOSYSTEMS['scala'], 'Scala')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.sbt').write_text('name := "demo"\n', encoding='utf-8')
            commands = test_commands(root)
            selected = select_test_commands(commands, args.ecosystem)
            self.assertEqual(selected, [
                {'ecosystem': 'Scala', 'argv': ['sbt', 'test'], 'reason': 'build.sbt'},
            ])


if __name__ == '__main__':
    unittest.main()
