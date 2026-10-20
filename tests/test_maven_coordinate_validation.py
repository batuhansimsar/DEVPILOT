"""Privacy regressions for untrusted Maven dependency coordinates."""

import unittest

from devpilot.maven_deps import parse_maven_dependencies


class MavenCoordinateValidationTests(unittest.TestCase):
    def test_valid_coordinates_and_profile_dependencies(self):
        pom = '''<project xmlns="http://maven.apache.org/POM/4.0.0">
            <dependencies><dependency>
                <groupId> org.example_internal </groupId><artifactId>lib-2.core</artifactId>
            </dependency></dependencies>
            <profiles><profile><dependencies><dependency>
                <groupId>org.tests</groupId><artifactId>test-fixtures</artifactId>
            </dependency></dependencies></profile></profiles>
        </project>'''
        self.assertEqual(parse_maven_dependencies(pom), {
            'dependencies': ['org.example_internal:lib-2.core'],
            'profile-dependencies': ['org.tests:test-fixtures'],
        })

    def test_invalid_or_private_coordinate_is_never_echoed(self):
        for key, value in (
            ('groupId', 'https://user:secret@example.invalid'),
            ('artifactId', '${private.token}'),
            ('artifactId', 'evil\u202eexe'),
            ('groupId', 'bad\nvalue'),
        ):
            group = value if key == 'groupId' else 'org.example'
            artifact = value if key == 'artifactId' else 'lib'
            pom = (f'<project><dependencies><dependency><groupId>{group}</groupId>'
                   f'<artifactId>{artifact}</artifactId></dependency></dependencies></project>')
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, 'invalid coordinate') as error:
                parse_maven_dependencies(pom)
            self.assertNotIn(value, str(error.exception))
            self.assertNotIn('secret', str(error.exception))

    def test_nested_elements_cannot_hide_trailing_content(self):
        pom = '''<project><dependencies><dependency>
            <groupId>org.safe<other>private-value</other></groupId>
            <artifactId>lib</artifactId>
        </dependency></dependencies></project>'''
        with self.assertRaisesRegex(ValueError, 'invalid coordinate') as error:
            parse_maven_dependencies(pom)
        self.assertNotIn('private-value', str(error.exception))

    def test_missing_coordinates_are_still_ignored(self):
        pom = '<project><dependencies><dependency><groupId>org.example</groupId></dependency></dependencies></project>'
        self.assertEqual(parse_maven_dependencies(pom), {'dependencies': []})


if __name__ == '__main__':
    unittest.main()
