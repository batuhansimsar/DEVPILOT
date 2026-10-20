"""Central NuGet PackageVersion inventory must be accurate and privacy safe."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dotnet_deps import parse_dotnet_dependencies


class DotnetCentralPackagesTests(unittest.TestCase):
    def test_central_package_versions_are_distinct_from_project_references(self):
        content = '''<Project>
          <PropertyGroup><ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally></PropertyGroup>
          <ItemGroup>
            <PackageVersion Include="Newtonsoft.Json" Version="13.0.3" />
            <PackageVersion Update="Microsoft.Extensions.Logging" Version="8.0.0" />
            <PackageVersion Include="Newtonsoft.Json" Version="13.0.2" />
            <PackageReference Include="NotACentralVersion" />
          </ItemGroup>
        </Project>'''
        self.assertEqual(parse_dotnet_dependencies(content, central=True), {
            'PackageVersion': ['Microsoft.Extensions.Logging', 'Newtonsoft.Json']
        })
        self.assertEqual(parse_dotnet_dependencies(content), {
            'PackageReference': ['NotACentralVersion']
        })

    def test_namespaced_central_packages_ignore_foreign_namespaces(self):
        content = '''<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003"
          xmlns:evil="urn:third-party">
          <ItemGroup><PackageVersion Include="Valid.Core" Version="1.0"/>
            <evil:PackageVersion Include="FalsePositive" />
            <evil:Group><PackageVersion Include="NestedFalsePositive" /></evil:Group>
          </ItemGroup>
        </Project>'''
        self.assertEqual(parse_dotnet_dependencies(content, central=True), {
            'PackageVersion': ['Valid.Core']
        })

    def test_central_package_invalid_ids_are_redacted(self):
        for bad in ('$(PackageName)', 'https://token:secret@example.test', '../unsafe'):
            content = f'<Project><ItemGroup><PackageVersion Include="{bad}" /></ItemGroup></Project>'
            with self.subTest(bad=bad), self.assertRaises(ValueError) as cm:
                parse_dotnet_dependencies(content, central=True)
            self.assertNotIn(bad, str(cm.exception))

    def test_central_package_outside_itemgroup_is_ignored(self):
        content = '''<Project><PropertyGroup>
            <PackageVersion Include="MetadataOnly" />
          </PropertyGroup>
          <ItemGroup><PackageVersion Include="ValidPackage"/></ItemGroup>
        </Project>'''
        self.assertEqual(parse_dotnet_dependencies(content, central=True), {
            'PackageVersion': ['ValidPackage']
        })

    def test_scan_directory_packages_props(self):
        from devpilot.deps import scan
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Directory.Packages.props').write_text('''<Project><ItemGroup>
              <PackageVersion Include="Serilog" Version="3.0.0"/>
            </ItemGroup></Project>''', encoding='utf-8')
            report = scan(root)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['totals'], {'.NET': 1})
        self.assertEqual(report['manifests'][0]['groups'], {'PackageVersion': ['Serilog']})
        self.assertEqual(report['manifests'][0]['path'], 'Directory.Packages.props')


if __name__ == '__main__':
    unittest.main()
