"""Regression tests for quoted dependency keys in Cargo.toml."""

import unittest

from devpilot.cargo_deps import parse_cargo_dependencies


class QuotedCargoDependenciesTests(unittest.TestCase):
    def test_quoted_dependency_names_in_regular_and_target_sections(self):
        cargo = """
[dependencies]
"serde" = "1"
'async-trait' = { version = "0.1" }
unquoted = "1"
[dev-dependencies]
"criterion" = "0.5"
[target.'cfg(unix)'.build-dependencies]
'cc' = "1"
[workspace.dependencies]
"serde" = "1"
"""
        self.assertEqual(parse_cargo_dependencies(cargo), {
            'dependencies': ['async-trait', 'serde', 'unquoted'],
            'dev-dependencies': ['criterion'],
            'build-dependencies': ['cc'],
        })

    def test_quoted_table_style_and_ignore_unrelated_or_malformed_keys(self):
        cargo = """
[package.metadata]
"not_a_dependency" = "secret"
[dependencies."serde_json"]
version = "1"
[dependencies]
"not-a-name with spaces" = "1"
# 'commented' = "1"
"tokio" = { version = "1", features = ["full"] }
"""
        self.assertEqual(parse_cargo_dependencies(cargo), {
            'dependencies': ['serde_json', 'tokio'],
        })
        self.assertNotIn('secret', str(parse_cargo_dependencies(cargo)))


if __name__ == '__main__':
    unittest.main()
