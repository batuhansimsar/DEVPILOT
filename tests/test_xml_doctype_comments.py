"""XML declaration detection must ignore comments/CDATA without allowing DTDs."""

import unittest

from devpilot.dotnet_deps import parse_dotnet_dependencies
from devpilot.maven_deps import parse_maven_dependencies


class XMLDoctypeDetectionTests(unittest.TestCase):
    def test_maven_comment_and_cdata_are_not_doctype_declarations(self):
        pom = '''<project xmlns="http://maven.apache.org/POM/4.0.0">
            <!-- A comment mentioning <!DOCTYPE and <!ENTITY is harmless. -->
            <description><![CDATA[<!DOCTYPE note><!ENTITY sample "text">]]></description>
            <dependencies><dependency><groupId>org.example</groupId>
                <artifactId>core</artifactId></dependency></dependencies>
        </project>'''
        self.assertEqual(parse_maven_dependencies(pom), {'dependencies': ['org.example:core']})

    def test_dotnet_comment_and_cdata_are_not_doctype_declarations(self):
        project = '''<Project>
            <!-- <!DOCTYPE Project [<!ENTITY secret "foo">] -->
            <PropertyGroup><Description><![CDATA[<!DOCTYPE harmless>]]></Description></PropertyGroup>
            <ItemGroup><PackageReference Include="Example.Core" Version="2.0" /></ItemGroup>
        </Project>'''
        self.assertEqual(parse_dotnet_dependencies(project), {'PackageReference': ['Example.Core']})

    def test_real_doctype_and_entities_still_rejected(self):
        for parser, tag in ((parse_maven_dependencies, 'project'),
                            (parse_dotnet_dependencies, 'Project')):
            with self.subTest(tag=tag):
                xml = (f'<!DOCTYPE {tag} [<!ENTITY leak SYSTEM "file:///private/secret">]'
                       f'><{tag}>&leak;</{tag}>')
                with self.assertRaisesRegex(ValueError, '^DTD and XML entities are not supported$') as error:
                    parser(xml)
                self.assertNotIn('private', str(error.exception))

    def test_dtd_without_entity_is_rejected(self):
        for parser, tag in ((parse_maven_dependencies, 'project'),
                            (parse_dotnet_dependencies, 'Project')):
            with self.subTest(tag=tag):
                with self.assertRaisesRegex(ValueError, 'DTD and XML entities are not supported'):
                    parser(f'<!DOCTYPE {tag}><{tag}/>')


if __name__ == '__main__':
    unittest.main()
