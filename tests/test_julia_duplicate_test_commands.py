"""Julia tests must be scheduled once even when other ecosystems are present."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import test_commands


class JuliaDuplicateTestCommandTests(unittest.TestCase):
    def test_pkg_test_is_planned_exactly_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'Project.toml').write_text('name = "Example"\n', encoding='utf-8')
            (root / 'test').mkdir()
            (root / 'test' / 'runtests.jl').write_text('using Test\n', encoding='utf-8')
            (root / 'go.mod').write_text('module demo\n', encoding='utf-8')
            commands = test_commands(root)
            julia_commands = [command for command in commands if command['ecosystem'] == 'Julia']
            self.assertEqual(len(julia_commands), 1)
            self.assertEqual(julia_commands[0]['argv'], [
                'julia', '--project=.', '-e', 'using Pkg; Pkg.test()',
            ])


if __name__ == '__main__':
    unittest.main()
