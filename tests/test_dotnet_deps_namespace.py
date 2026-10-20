"""Prevent foreign XML elements from becoming false .NET dependencies."""

import unittest

from devpilot.dotnet_deps import parse_dotnet_dependencies


class DotnetDependencyNamespaceTests(unittest.TestCase):
    def test_modern_project_recognizes_includes_updates_and_conditions(self):
        content = '''<Project><ItemGroup>
            <PackageReference Include="Serilog" Version="3.0"/>
            <PackageReference Update="Newtonsoft.Json" Version="13.0"/>
            <When Condition="true"><PackageReference Include="MediatR"/></When>
        </ItemGroup></Project>'''
        self.assertEqual(parse_dotnet_dependencies(content), {
            'PackageReference': ['MediatR', 'Newtonsoft.Json', 'Serilog'],
        })

    def test_legacy_msbuild_namespace_is_supported(self):
        content = '''<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
          <ItemGroup><PackageReference Include="NUnit"/></ItemGroup>
        </Project>'''
        self.assertEqual(parse_dotnet_dependencies(content), {'PackageReference': ['NUnit']})

    def test_foreign_namespace_packages_are_not_counted(self):
        content = '''<Project xmlns:meta="urn:devpilot:metadata">
          <ItemGroup><meta:PackageReference Include="not-a-real-package"/>
          <PackageReference Include="Serilog"/></ItemGroup>
        </Project>'''
        self.assertEqual(parse_dotnet_dependencies(content), {'PackageReference': ['Serilog']})

    def test_foreign_project_root_is_rejected(self):
        content = '''<other:Project xmlns:other="urn:external">
            <other:PackageReference Include="fake"/>
        </other:Project>'''
        with self.assertRaisesRegex(ValueError, 'MSBuild Project'):
            parse_dotnet_dependencies(content)

    def test_document_type_is_rejected(self):
        content = '<!DOCTYPE Project [<!ENTITY exploit SYSTEM "file:///etc/passwd">]><Project />'
        with self.assertRaisesRegex(ValueError, 'DTD'):
            parse_dotnet_dependencies(content)


if __name__ == '__main__':
    unittest.main()
