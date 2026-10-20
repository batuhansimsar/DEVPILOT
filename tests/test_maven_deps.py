"""Tests for safe, namespaced Maven manifest dependency inventory."""

import unittest
import xml.etree.ElementTree as ET

from devpilot.maven_deps import parse_maven_dependencies


class MavenDependenciesTests(unittest.TestCase):
    def test_namespaced_project_includes_only_direct_dependencies(self):
        pom = '''<project xmlns="http://maven.apache.org/POM/4.0.0">
            <dependencies>
                <dependency><groupId>org.example</groupId>
                    <artifactId>core</artifactId><version>1.2-secret</version></dependency>
                <dependency><groupId>org.alpha</groupId><artifactId>client</artifactId></dependency>
                <dependency><groupId>org.example</groupId><artifactId>core</artifactId></dependency>
                <dependency><groupId>org.incomplete</groupId></dependency>
            </dependencies>
            <dependencyManagement><dependencies><dependency>
                <groupId>managed</groupId><artifactId>not-installed</artifactId>
            </dependency></dependencies></dependencyManagement>
            <build><plugins><plugin><dependencies><dependency>
                <groupId>plugin</groupId><artifactId>not-runtime</artifactId>
            </dependency></dependencies></plugin></plugins></build>
        </project>'''
        result = parse_maven_dependencies(pom)
        self.assertEqual(result, {'dependencies': ['org.alpha:client', 'org.example:core']})
        self.assertNotIn('1.2-secret', str(result))

    def test_unqualified_xml_and_empty_projects(self):
        self.assertEqual(parse_maven_dependencies('<project/>'), {'dependencies': []})
        self.assertEqual(
            parse_maven_dependencies('<project><dependencies><dependency>'
                                     '<groupId>demo</groupId><artifactId>api</artifactId>'
                                     '</dependency></dependencies></project>'),
            {'dependencies': ['demo:api']},
        )

    def test_rejects_external_entities_before_parsing(self):
        for payload in (
            '<!DOCTYPE project SYSTEM "file:///etc/passwd"><project/>',
            '<!DOCTYPE project [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
            '<project><dependencies>&x;</dependencies></project>',
        ):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, 'DTD'):
                parse_maven_dependencies(payload)

    def test_malformed_or_unexpected_root_is_rejected(self):
        with self.assertRaises(ET.ParseError):
            parse_maven_dependencies('<project>')
        with self.assertRaisesRegex(ValueError, 'root'):
            parse_maven_dependencies('<settings/>')


if __name__ == '__main__':
    unittest.main()
