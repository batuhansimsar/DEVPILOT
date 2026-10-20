"""Cargo inventory must not count missing dependency value declarations."""
import unittest

from devpilot.cargo_deps import parse_cargo_dependencies


class CargoMissingValueTests(unittest.TestCase):
    def test_ignores_missing_values_and_inline_comment_only_lines(self):
        content = '''[dependencies]
valid = "1.0"
missing =
comment_only = # incomplete
inline = { version = "1.0" }
quoted = '2.0'
[dev-dependencies]
missing_dev =  # pending
pytest_equivalent = "3.0"
'''
        self.assertEqual(parse_cargo_dependencies(content), {
            'dependencies': ['inline', 'quoted', 'valid'],
            'dev-dependencies': ['pytest_equivalent'],
        })

    def test_comment_character_inside_string_stays_valid(self):
        self.assertEqual(parse_cargo_dependencies('[dependencies]\nkept = "git#branch"\n'), {'dependencies': ['kept']})


if __name__ == '__main__':
    unittest.main()
