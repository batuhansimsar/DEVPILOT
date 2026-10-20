"""Regression tests for table-style Cargo dependency declarations."""

import unittest

from devpilot.cargo_deps import parse_cargo_dependencies


class CargoDependencyParserTests(unittest.TestCase):
    def test_table_style_and_standard_sections(self):
        toml = '''
[package]
name = "sample"
[dependencies]
serde_json = "1"
[dependencies.serde]
version = "1"
features = ["derive"]
[dev-dependencies.criterion]
version = "0.5"
[target.'cfg(unix)'.build-dependencies.cc]
version = "1"
[target.'cfg(windows)'.dependencies.winapi]
version = "0.3"
'''
        self.assertEqual(parse_cargo_dependencies(toml), {
            'dependencies': ['serde', 'serde_json', 'winapi'],
            'dev-dependencies': ['criterion'],
            'build-dependencies': ['cc'],
        })

    def test_workspace_and_target_inline_dependencies(self):
        toml = '''
[workspace.dependencies]
tokio = "1"
[target.'cfg(unix)'.dev-dependencies]
proptest = "1"
'''
        self.assertEqual(parse_cargo_dependencies(toml), {
            'dependencies': ['tokio'], 'dev-dependencies': ['proptest'],
        })

    def test_unrelated_metadata_and_values_not_reported(self):
        toml = '''
[package.metadata.dependencies]
not_a_dependency = "secret-token"
[dependencies.tokio]
version = "secret-token"
[profile.release]
codegen_units = 1
'''
        result = parse_cargo_dependencies(toml)
        self.assertEqual(result, {'dependencies': ['tokio']})
        self.assertNotIn('secret-token', str(result))


if __name__ == '__main__':
    unittest.main()
