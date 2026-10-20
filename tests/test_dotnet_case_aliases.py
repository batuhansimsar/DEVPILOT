"""NuGet IDs are case-insensitive across project and central manifests."""

import unittest

from devpilot.dotnet_deps import parse_dotnet_dependencies


class DotnetCaseAliasesTests(unittest.TestCase):
    def test_project_references_are_deduplicated_across_casing_aliases(self):
        content = '''<Project><ItemGroup>
            <PackageReference Include="serilog" Version="1.0" />
            <PackageReference Update="Serilog" Version="2.0" />
            <PackageReference Include="SERILOG" Version="3.0" />
            <PackageReference Include="Newtonsoft.Json" />
        </ItemGroup></Project>'''
        self.assertEqual(parse_dotnet_dependencies(content), {
            'PackageReference': ['Newtonsoft.Json', 'SERILOG'],
        })

    def test_central_versions_use_the_same_case_insensitive_rules(self):
        content = '''<Project><ItemGroup>
            <PackageVersion Include="microsoft.extensions.logging" />
            <PackageVersion Update="Microsoft.Extensions.Logging" />
            <PackageVersion Include="xunit" />
        </ItemGroup></Project>'''
        self.assertEqual(parse_dotnet_dependencies(content, central=True), {
            'PackageVersion': ['Microsoft.Extensions.Logging', 'xunit'],
        })

    def test_canonical_spelling_is_independent_of_manifest_order(self):
        entries = ('<PackageReference Include="test.package" />',
                   '<PackageReference Include="Test.Package" />')
        first = '<Project><ItemGroup>' + ''.join(entries) + '</ItemGroup></Project>'
        second = '<Project><ItemGroup>' + ''.join(reversed(entries)) + '</ItemGroup></Project>'
        self.assertEqual(parse_dotnet_dependencies(first), parse_dotnet_dependencies(second))

    def test_distinct_names_remain_distinct(self):
        content = '''<Project><ItemGroup><PackageReference Include="foo.bar"/>
          <PackageReference Include="foo-bar"/>
          <PackageReference Include="foo_bar"/></ItemGroup></Project>'''
        self.assertEqual(parse_dotnet_dependencies(content), {
            'PackageReference': ['foo-bar', 'foo.bar', 'foo_bar'],
        })


if __name__ == '__main__':
    unittest.main()
