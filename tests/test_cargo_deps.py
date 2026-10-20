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


    def test_comments_after_section_headers(self):
        toml = '''
[dependencies] # production dependencies
serde = "1" # version is intentionally ignored
[dev-dependencies]# testing dependencies
proptest = "1"
[workspace.dependencies] # shared packages
anyhow = "1"
[target.'cfg(unix)'.build-dependencies.cc] # build script
version = "1"
'''
        self.assertEqual(parse_cargo_dependencies(toml), {
            'dependencies': ['anyhow', 'serde'],
            'dev-dependencies': ['proptest'],
            'build-dependencies': ['cc'],
        })

    def test_hash_inside_quoted_target_is_not_a_comment(self):
        toml = '''
[target.'cfg(feature = "special#feature")'.dependencies] # trailing comment
my_crate = "1"
[target.'cfg(feature = "another#feature")'.dev-dependencies.assert_cmd] # note
version = "2"
'''
        self.assertEqual(parse_cargo_dependencies(toml), {
            'dependencies': ['my_crate'], 'dev-dependencies': ['assert_cmd'],
        })

    def test_commented_metadata_does_not_create_false_dependencies(self):
        toml = '''
[dependencies] # legit
serde = "1"
[package.metadata.dependencies] # not Cargo dependencies
private_setting = "secret"
# [dependencies]
# should_not_count = "1"
'''
        self.assertEqual(parse_cargo_dependencies(toml), {'dependencies': ['serde']})



    def test_malformed_section_does_not_inherit_dependency_group(self):
        content = '''
[dependencies]
serde = "1"
[[invalid-table]]
ghost_dependency = "secret"
[package.metadata]
another_ghost = "secret"
'''
        self.assertEqual(parse_cargo_dependencies(content), {'dependencies': ['serde']})


    def test_whitespace_around_toml_table_keys(self):
        manifest = '''
[ dependencies ]
serde_json = "1"
[dependencies . serde]
version = "1"
[target . 'cfg(unix)' . dev-dependencies]
proptest = "1"
'''
        self.assertEqual(parse_cargo_dependencies(manifest), {
            'dependencies': ['serde', 'serde_json'],
            'dev-dependencies': ['proptest'],
        })


if __name__ == '__main__':
    unittest.main()
