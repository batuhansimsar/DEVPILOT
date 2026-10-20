"""End-to-end regression tests for Maven dependency inventory."""

import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.deps import main, scan


class MavenDependencyInventoryIntegrationTests(unittest.TestCase):
    def test_namespaced_pom_is_counted_without_versions_or_managed_dependencies(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pom.xml').write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0">
                <dependencies>
                    <dependency><groupId>org.example</groupId><artifactId>core</artifactId>
                        <version>do-not-report-version</version></dependency>
                    <dependency><groupId>org.example</groupId><artifactId>core</artifactId></dependency>
                </dependencies>
                <dependencyManagement><dependencies><dependency>
                    <groupId>managed</groupId><artifactId>not-direct</artifactId>
                </dependency></dependencies></dependencyManagement>
                <build><plugins><plugin><dependencies><dependency>
                    <groupId>plugin</groupId><artifactId>not-direct</artifactId>
                </dependency></dependencies></plugin></plugins></build>
            </project>''', encoding='utf-8')
            report = scan(root)
            self.assertEqual(report['warnings'], [])
            self.assertEqual(report['totals'], {'Java': 1})
            self.assertEqual(report['manifests'][0]['groups'], {'dependencies': ['org.example:core']})
            self.assertNotIn('do-not-report-version', json.dumps(report))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['--path', str(root), '--json']), 0)
            self.assertEqual(json.loads(output.getvalue())['totals'], {'Java': 1})

    def test_malformed_pom_is_a_warning_and_cli_returns_failure(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pom.xml').write_text('<project><dependencies>', encoding='utf-8')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['--path', str(root), '--json']), 1)
            report = json.loads(output.getvalue())
            self.assertEqual(report['manifests'], [])
            self.assertEqual(len(report['warnings']), 1)
            self.assertIn('pom.xml', report['warnings'][0])

    def test_pom_with_external_entity_is_rejected_without_exposing_file_data(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pom.xml').write_text(
                '<!DOCTYPE project [<!ENTITY leak SYSTEM "file:///etc/passwd">]>'
                '<project><dependencies>&leak;</dependencies></project>', encoding='utf-8')
            report = scan(root)
            self.assertEqual(report['manifests'], [])
            self.assertEqual(len(report['warnings']), 1)
            self.assertIn('DTD and XML entities are not supported', report['warnings'][0])
            self.assertNotIn('/etc/passwd', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
