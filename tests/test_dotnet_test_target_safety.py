"""Unsafe .NET test target filenames must not become command options or paths."""

import unittest

from devpilot.dotnet_manifests import dotnet_test_target


class DotnetTargetSafetyTests(unittest.TestCase):
    def test_preserves_safe_solution_filter_and_project_precedence(self):
        self.assertEqual(dotnet_test_target({'Api.sln', 'Api.slnf'}), 'Api.sln')
        self.assertEqual(dotnet_test_target({'Api.slnf', 'Api.csproj'}), 'Api.slnf')
        self.assertIsNone(dotnet_test_target({'A.sln', 'B.slnx', 'Api.slnf'}))

    def test_rejects_option_and_path_shaped_filenames(self):
        for unsafe in ('--help.sln', '-v.slnf', '../outside.sln', 'child/project.csproj',
                       'child\\project.csproj', 'bad\nname.sln', 'bad\rname.sln',
                       'bad\x00.sln'):
            with self.subTest(name=unsafe):
                self.assertIsNone(dotnet_test_target({unsafe}))

    def test_safe_target_is_not_hidden_by_unsafe_filename(self):
        self.assertEqual(dotnet_test_target({'--help.sln', 'Api.csproj'}), 'Api.csproj')
        self.assertEqual(dotnet_test_target({'--help.sln', 'Api.sln'}), 'Api.sln')


if __name__ == '__main__':
    unittest.main()
