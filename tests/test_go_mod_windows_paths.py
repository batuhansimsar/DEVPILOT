"""Cross-platform Go module path component validation."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModuleWindowsPathTests(unittest.TestCase):
    def test_rejects_windows_device_names_and_extensions(self):
        source = (
            'require example.org/CON v1.0.0\n'
            'require example.org/nul.txt v1.0.0\n'
            'require example.org/COM9.config v1.0.0\n'
            'require example.org/lpt1 v1.0.0\n'
            'require example.org/valid v1.0.0\n'
        )
        self.assertEqual(parse_go_requirements(source), ['example.org/valid'])

    def test_rejects_short_name_aliases_in_all_supported_syntaxes(self):
        source = (
            'require example.org/PROGRA~1 v1.0.0\n'
            'require (\n'
            '  "example.org/cache~20.txt" v1.0.0\n'
            '  `example.org/LIB~4` `v1.0.0`\n'
            '  example.org/lib~next v1.0.0\n'
            '  example.org/pre~2fix v1.0.0\n'
            ')\n'
        )
        self.assertEqual(parse_go_requirements(source), [
            'example.org/lib~next', 'example.org/pre~2fix',
        ])

    def test_nonreserved_names_and_nonalias_tildes_are_accepted(self):
        names = ['example.org/console', 'example.org/COM10', 'example.org/auxiliary',
                 'example.org/special~next', 'example.org/name~1suffix']
        source = ''.join(f'require {name} v1.0.0\n' for name in names)
        self.assertEqual(parse_go_requirements(source), sorted(names))


if __name__ == '__main__':
    unittest.main()
