"""Cargo TOML dotted assignments specify real dependencies, not version keys."""

import tomllib
import unittest

from devpilot.cargo_deps import parse_cargo_dependencies


class CargoDottedKeyTests(unittest.TestCase):
    def test_dotted_assignments_in_regular_workspace_and_target_groups(self):
        source = '''
[dependencies]
serde.version = "1"
"serde_json" . features = ["std"]
'async-trait'.package = "async-trait"
serde.features = ["derive"]
[workspace.dependencies]
tokio . version = "1"
[target.'cfg(unix)'.build-dependencies]
cc.version = "1"
[dev-dependencies]
criterion = "0.5"
[package.metadata]
not_a_dependency.version = "secret"
'''
        tomllib.loads(source)  # Validate the fixture against TOML syntax.
        self.assertEqual(parse_cargo_dependencies(source), {
            'dependencies': ['async-trait', 'serde', 'serde_json', 'tokio'],
            'build-dependencies': ['cc'],
            'dev-dependencies': ['criterion'],
        })
        self.assertNotIn('secret', str(parse_cargo_dependencies(source)))

    def test_comments_multiline_text_and_invalid_keys_are_not_dependencies(self):
        source = '''
[package]
description = """
[dependencies]
fake.version = "private"
"""
[dependencies]
# ghost.version = "1"
"bad name".version = "1"
real.version = "1"
'''
        self.assertEqual(parse_cargo_dependencies(source), {'dependencies': ['real']})


if __name__ == '__main__':
    unittest.main()
