"""Maven namespace and ambiguity regression tests."""

import unittest

from devpilot.maven_deps import parse_maven_dependencies


class MavenNamespaceTests(unittest.TestCase):
    def test_only_maven_elements_are_inventoried(self):
        for namespace in ('', ' xmlns="http://maven.apache.org/POM/4.0.0"'):
            with self.subTest(namespace=namespace):
                xml = f'''<project{namespace} xmlns:other="urn:foreign">
                    <dependencies>
                        <dependency><groupId>org.safe</groupId>
                            <artifactId>core</artifactId></dependency>
                        <other:dependency><other:groupId>org.fake</other:groupId>
                            <other:artifactId>not-a-dependency</other:artifactId></other:dependency>
                        <dependency><other:groupId>org.fake</other:groupId>
                            <artifactId>incomplete</artifactId></dependency>
                    </dependencies>
                    <other:dependencies><dependency><groupId>org.fake</groupId>
                        <artifactId>ignored</artifactId></dependency></other:dependencies>
                </project>'''
                self.assertEqual(parse_maven_dependencies(xml),
                                 {'dependencies': ['org.safe:core']})

    def test_foreign_project_namespace_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Maven project'):
            parse_maven_dependencies('<x:project xmlns:x="urn:foreign"/>')

    def test_ambiguous_coordinates_rejected_without_leaking_values(self):
        xml = '''<project><dependencies><dependency>
            <groupId>private-one</groupId><groupId>private-two</groupId>
            <artifactId>lib</artifactId>
        </dependency></dependencies></project>'''
        with self.assertRaises(ValueError) as caught:
            parse_maven_dependencies(xml)
        self.assertNotIn('private-', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
