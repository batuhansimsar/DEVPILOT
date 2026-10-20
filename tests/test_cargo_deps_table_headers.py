"""Regression tests for Cargo dependency table scope and quoted keys."""

import unittest

from devpilot.cargo_deps import parse_cargo_dependencies


class CargoTableHeaderTests(unittest.TestCase):
    def test_trailing_comments_on_table_headers(self):
        toml = '''
[dependencies] # use crates.io
serde = "1"
[workspace.dependencies.anyhow] # workspace crate
version = "1"
[target.'cfg(target_os = "linux")'.dev-dependencies] # platform tests
proptest = "1"
[build-dependencies.cc] # builder
version = "1"
'''
        self.assertEqual(parse_cargo_dependencies(toml), {
            'dependencies': ['anyhow', 'serde'],
            'dev-dependencies': ['proptest'],
            'build-dependencies': ['cc'],
        })

    def test_unrelated_nested_metadata_is_not_counted(self):
        toml = '''
[workspace.package.metadata.dependencies]
pretend = "secret-registry-token"
[target.'cfg(unix)'.metadata.dependencies]
pretend2 = "1"
[target.'cfg(unix)'.metadata.dependencies.fake]
version = "1"
[workspace.custom.dependencies.other]
version = "1"
'''
        self.assertEqual(parse_cargo_dependencies(toml), {})

    def test_quoted_dotted_target_and_array_table_reset(self):
        toml = '''
[target.'cfg(feature = "foo.bar")'.dependencies.serde]
version = "1"
[dependencies] # start dependency table
reqwest = "0.12"
[[bin]]
name = "not_a_dependency"
[dependencies."serde_json"] # quoted crate key
version = "1"
'''
        self.assertEqual(parse_cargo_dependencies(toml), {
            'dependencies': ['reqwest', 'serde', 'serde_json'],
        })


if __name__ == '__main__':
    unittest.main()
