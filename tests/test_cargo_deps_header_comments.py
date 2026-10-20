"""Cargo TOML table header comment regressions."""
import unittest
from devpilot.cargo_deps import parse_cargo_dependencies


class CargoCommentTests(unittest.TestCase):
    def test_comments_on_group_headers_do_not_misclassify(self):
        content = '''
[dev-dependencies] # test-only packages
criterion = "0.5"
[dependencies] # production packages
serde = { version = "1", features = ["derive"] }
[build-dependencies] # build-time
cc = "1"
'''
        self.assertEqual(parse_cargo_dependencies(content), {
            'dev-dependencies': ['criterion'],
            'dependencies': ['serde'],
            'build-dependencies': ['cc'],
        })

    def test_table_style_comments_and_hash_inside_quoted_target(self):
        content = '''
[target.'cfg(feature = "embedded#v2")'.dependencies] # valid TOML comment
sensor = "1"
[target.'cfg(unix)'.build-dependencies.cc] # table-style package
version = "1"
[dev-dependencies.insta] # more tests
version = "1"
'''
        self.assertEqual(parse_cargo_dependencies(content), {
            'dependencies': ['sensor'],
            'build-dependencies': ['cc'],
            'dev-dependencies': ['insta'],
        })

    def test_malformed_headers_do_not_leak_previous_section(self):
        content = '''
[dependencies]
serde = "1"
[not-a-valid-table] unexpected
should_not_count = "secret"
[dev-dependencies] # recovered
criterion = "1"
'''
        self.assertEqual(parse_cargo_dependencies(content), {
            'dependencies': ['serde'],
            'dev-dependencies': ['criterion'],
        })

    def test_regular_sections_still_work(self):
        content = '''
[package]
name = "test"
[dependencies]
serde_json = "1"
[dependencies.serde]
version = "1"
[dev-dependencies.criterion]
version = "0.5"
[target.'cfg(unix)'.build-dependencies.cc]
version = "1"
[target.'cfg(windows)'.dependencies.winapi]
version = "0.3"
'''
        self.assertEqual(parse_cargo_dependencies(content), {
            'dependencies': ['serde', 'serde_json', 'winapi'],
            'dev-dependencies': ['criterion'],
            'build-dependencies': ['cc'],
        })


if __name__ == '__main__':
    unittest.main()
