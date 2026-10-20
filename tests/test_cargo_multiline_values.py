"""Cargo multiline TOML string values should be discovered, but not injected."""

import unittest

from devpilot.cargo_deps import parse_cargo_dependencies


class CargoMultilineValuesTests(unittest.TestCase):
    def test_inline_triple_quoted_version(self):
        source = "[dependencies]\nserde = \"\"\"1.0\"\"\"\ntokio = '''1.0'''\n"
        self.assertEqual(parse_cargo_dependencies(source), {'dependencies': ['serde', 'tokio']})

    def test_multiline_value_and_embedded_fake_table(self):
        source = ('[dependencies]\nserde = """1.0\n'
                  '[dev-dependencies]\nnot-a-dependency = "1"\n"""\n'
                  "tokio = '''\n1.0\n'''\n")
        self.assertEqual(parse_cargo_dependencies(source), {'dependencies': ['serde', 'tokio']})

    def test_unterminated_multiline_declaration_is_not_counted(self):
        source = '[dependencies]\nvalid = "1"\nincomplete = """secret\n'
        self.assertEqual(parse_cargo_dependencies(source), {'dependencies': ['valid']})

    def test_metadata_multiline_does_not_inject_dependency(self):
        source = ('[package]\ndescription = """\n[dependencies]\nghost = "1"\n"""\n'
                  '[dependencies]\nreal = "2"\n')
        self.assertEqual(parse_cargo_dependencies(source), {'dependencies': ['real']})


if __name__ == '__main__':
    unittest.main()
