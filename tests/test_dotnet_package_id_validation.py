"""Protect dependency reports against unsafe .NET PackageReference names."""

import unittest

from devpilot.dotnet_deps import parse_dotnet_dependencies


class DotnetPackageIdValidationTests(unittest.TestCase):
    def test_ordinary_nuget_ids_and_legacy_namespace_are_supported(self):
        xml = '''<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
          <ItemGroup>
            <PackageReference Include="Microsoft.Extensions.Logging" Version="9.0.0" />
            <PackageReference Update="xunit.runner-visualstudio" />
            <PackageReference Include="FSharp_Core" />
          </ItemGroup>
        </Project>'''
        self.assertEqual(parse_dotnet_dependencies(xml), {
            'PackageReference': [
                'FSharp_Core', 'Microsoft.Extensions.Logging', 'xunit.runner-visualstudio'
            ]
        })

    def test_non_package_names_are_rejected_without_echoing_secrets(self):
        for name in (
            'https://user:secret@example.com/pkg', '$(PrivatePackage)',
            'Bad Package', 'Bad\nName', 'Bad;Injected', 'Name\\Path',
            'a' * 101,
        ):
            with self.subTest(name=name), self.assertRaises(ValueError) as failure:
                parse_dotnet_dependencies(
                    '<Project><ItemGroup><PackageReference Include="'
                    + name.replace('&', '&amp;').replace('"', '&quot;')
                    + '" /></ItemGroup></Project>'
                )
            self.assertIn('invalid PackageReference identifier', str(failure.exception))
            self.assertNotIn(name, str(failure.exception))
            self.assertNotIn('secret', str(failure.exception))

    def test_foreign_namespace_cannot_inject_untrusted_names(self):
        xml = '''<Project xmlns:foreign="urn:metadata"><ItemGroup>
          <foreign:PackageReference Include="https://user:secret@example.org" />
          <PackageReference Include="Serilog" />
        </ItemGroup></Project>'''
        self.assertEqual(parse_dotnet_dependencies(xml), {'PackageReference': ['Serilog']})

    def test_names_are_not_overvalidated_when_optional(self):
        self.assertEqual(parse_dotnet_dependencies('<Project><ItemGroup><PackageReference /></ItemGroup></Project>'), {'PackageReference': []})

    def test_out_of_scope_and_nested_foreign_references_are_ignored(self):
        xml = '''<Project xmlns:foreign="urn:metadata">
          <PackageReference Include="https://user:secret@example.org/ignored" />
          <foreign:Container><ItemGroup>
            <PackageReference Include="https://user:secret@example.org/ignored" />
          </ItemGroup></foreign:Container>
          <ItemGroup><PackageReference Include="Serilog" /></ItemGroup>
        </Project>'''
        self.assertEqual(parse_dotnet_dependencies(xml), {'PackageReference': ['Serilog']})


if __name__ == '__main__':
    unittest.main()
