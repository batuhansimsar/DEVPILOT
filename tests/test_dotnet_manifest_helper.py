"""Pure unit tests for the shared .NET manifest classifier."""

import unittest

from devpilot.dotnet_manifests import dotnet_test_target, is_dotnet_manifest


class DotnetManifestHelperTests(unittest.TestCase):
    def test_solution_filter_markers_and_lookalikes(self):
        self.assertTrue(is_dotnet_manifest('Api.slnf'))
        self.assertTrue(is_dotnet_manifest('Api.SLNF'))
        self.assertTrue(is_dotnet_manifest('Directory.Packages.props'))
        self.assertFalse(is_dotnet_manifest('Api.slnf.bak'))
        self.assertFalse(is_dotnet_manifest('Api.slnff'))

    def test_prefer_full_solution_then_filter_then_project(self):
        self.assertEqual(dotnet_test_target({'Api.sln', 'Api.slnf'}), 'Api.sln')
        self.assertEqual(dotnet_test_target({'Api.slnf', 'Api.csproj'}), 'Api.slnf')
        self.assertEqual(dotnet_test_target({'Api.csproj'}), 'Api.csproj')

    def test_ambiguous_full_solutions_cannot_be_overridden_by_filter(self):
        self.assertIsNone(dotnet_test_target({'A.sln', 'B.slnx', 'One.slnf'}))
        self.assertIsNone(dotnet_test_target({'A.slnf', 'B.slnf'}))
        self.assertIsNone(dotnet_test_target(set()))


if __name__ == '__main__':
    unittest.main()
