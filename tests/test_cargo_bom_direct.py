"""Direct callers should see the same UTF-8 BOM behavior as scanner reads."""
import unittest
from devpilot.cargo_deps import parse_cargo_dependencies


class CargoDirectBOMTests(unittest.TestCase):
    def test_first_dependency_table_after_bom(self):
        content = '\ufeff[dependencies]\nserde = "1"\n[dev-dependencies]\ninsta = "1"\n'
        self.assertEqual(parse_cargo_dependencies(content), {
            'dependencies': ['serde'], 'dev-dependencies': ['insta'],
        })

    def test_bom_before_workspace_table(self):
        content = '\ufeff[workspace.dependencies]\nserde.version = "1"\n'
        self.assertEqual(parse_cargo_dependencies(content), {'dependencies': ['serde']})

    def test_embedded_bom_does_not_create_dependency(self):
        content = '[dependencies]\nvalid = "1"\n\ufeffinvalid = "2"\n'
        self.assertEqual(parse_cargo_dependencies(content), {'dependencies': ['valid']})


if __name__ == '__main__':
    unittest.main()
