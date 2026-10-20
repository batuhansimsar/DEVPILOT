"""Foreign-namespace extensions must not masquerade as Maven dependencies."""

import unittest

from devpilot.maven_deps import parse_maven_dependencies


class MavenNamespaceIsolationTests(unittest.TestCase):
    def test_namespaced_pom_ignores_foreign_dependencies_and_coordinates(self):
        pom = '''<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:ext="urn:extension">
            <dependencies>
                <ext:dependency><ext:groupId>foreign</ext:groupId>
                    <ext:artifactId>artifact</ext:artifactId></ext:dependency>
                <dependency><ext:groupId>not-maven</ext:groupId>
                    <artifactId>no-group</artifactId></dependency>
                <dependency><groupId>org.real</groupId><artifactId>core</artifactId>
                    <ext:artifactId>spoofed</ext:artifactId></dependency>
            </dependencies>
            <ext:dependencies><dependency><groupId>hidden</groupId>
                <artifactId>not-direct</artifactId></dependency></ext:dependencies>
        </project>'''
        self.assertEqual(parse_maven_dependencies(pom), {'dependencies': ['org.real:core']})

    def test_unnamespaced_pom_ignores_foreign_tags(self):
        pom = '''<project xmlns:ext="urn:extension">
            <ext:dependencies><dependency><groupId>wrong</groupId>
                <artifactId>outer</artifactId></dependency></ext:dependencies>
            <dependencies>
                <ext:dependency><groupId>wrong</groupId>
                    <artifactId>inner</artifactId></ext:dependency>
                <dependency><groupId>org.real</groupId>
                    <ext:artifactId>spoofed</ext:artifactId><artifactId>api</artifactId></dependency>
            </dependencies>
        </project>'''
        self.assertEqual(parse_maven_dependencies(pom), {'dependencies': ['org.real:api']})


if __name__ == '__main__':
    unittest.main()
