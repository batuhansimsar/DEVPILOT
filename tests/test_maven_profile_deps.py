"""Profile requirements are conditional and must not pollute direct dependencies."""

import unittest

from devpilot.maven_deps import parse_maven_dependencies


class MavenProfileDependenciesTests(unittest.TestCase):
    def test_profiles_separate_from_direct_and_deduplicate(self):
        pom = '''<project xmlns="http://maven.apache.org/POM/4.0.0">
            <dependencies><dependency><groupId>org.example</groupId><artifactId>core</artifactId></dependency></dependencies>
            <profiles>
              <profile><id>dev</id><dependencies>
                <dependency><groupId>org.example</groupId><artifactId>debug</artifactId><version>do-not-expose</version></dependency>
              </dependencies></profile>
              <profile><id>ci</id><dependencies>
                <dependency><groupId>org.example</groupId><artifactId>debug</artifactId></dependency>
                <dependency><groupId>org.example</groupId><artifactId>mock</artifactId></dependency>
              </dependencies></profile>
            </profiles>
            <dependencyManagement><dependencies><dependency><groupId>excluded</groupId><artifactId>managed</artifactId></dependency></dependencies></dependencyManagement>
        </project>'''
        result = parse_maven_dependencies(pom)
        self.assertEqual(result, {'dependencies': ['org.example:core'],
                                  'profile-dependencies': ['org.example:debug', 'org.example:mock']})
        self.assertNotIn('do-not-expose', str(result))
        self.assertNotIn('excluded', str(result))

    def test_extension_nodes_and_profile_management_are_ignored(self):
        pom = '''<project xmlns:ext="urn:extensions">
          <profiles>
            <ext:profile><dependencies><dependency><groupId>ignored</groupId><artifactId>ext-profile</artifactId></dependency></dependencies></ext:profile>
            <profile>
              <ext:dependencies><dependency><groupId>ignored</groupId><artifactId>ext-dependencies</artifactId></dependency></ext:dependencies>
              <dependencyManagement><dependencies><dependency><groupId>ignored</groupId><artifactId>managed</artifactId></dependency></dependencies></dependencyManagement>
              <dependencies>
                <ext:dependency><groupId>ignored</groupId><artifactId>ext-dependency</artifactId></ext:dependency>
                <dependency><ext:groupId>ignored</ext:groupId><artifactId>missing-group</artifactId></dependency>
                <dependency><groupId>real</groupId><artifactId>from-profile</artifactId></dependency>
              </dependencies>
            </profile>
          </profiles>
        </project>'''
        self.assertEqual(parse_maven_dependencies(pom), {
            'dependencies': [], 'profile-dependencies': ['real:from-profile']})

    def test_no_profiles_preserves_existing_return_shape(self):
        self.assertEqual(parse_maven_dependencies('<project/>'), {'dependencies': []})

    def test_duplicate_coordinates_in_profile_are_rejected_without_values(self):
        pom = '''<project><profiles><profile><dependencies><dependency>
          <groupId>first-secret</groupId><groupId>second-secret</groupId>
          <artifactId>artifact</artifactId>
        </dependency></dependencies></profile></profiles></project>'''
        with self.assertRaises(ValueError) as ctx:
            parse_maven_dependencies(pom)
        self.assertNotIn('secret', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
