"""Integration regressions for Maven POM dependency inventories."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class MavenInventoryIntegrationTests(unittest.TestCase):
    def test_namespaced_pom_counts_only_direct_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text(
                """<project xmlns="http://maven.apache.org/POM/4.0.0">
                    <dependencies>
                        <dependency><groupId>org.example</groupId>
                            <artifactId>api</artifactId><version>private-version</version></dependency>
                        <dependency><groupId>org.alpha</groupId>
                            <artifactId>client</artifactId></dependency>
                        <dependency><groupId>org.example</groupId>
                            <artifactId>api</artifactId></dependency>
                    </dependencies>
                    <dependencyManagement><dependencies><dependency>
                        <groupId>managed</groupId><artifactId>excluded</artifactId>
                    </dependency></dependencies></dependencyManagement>
                    <build><plugins><plugin><dependencies><dependency>
                        <groupId>plugin</groupId><artifactId>excluded</artifactId>
                    </dependency></dependencies></plugin></plugins></build>
                </project>""",
                encoding="utf-8",
            )
            report = scan(root)
            self.assertEqual(report["warnings"], [])
            self.assertEqual(report["totals"], {"Java": 2})
            self.assertEqual(len(report["manifests"]), 1)
            self.assertEqual(report["manifests"][0]["groups"], {
                "dependencies": ["org.alpha:client", "org.example:api"],
            })
            self.assertNotIn("private-version", json.dumps(report))

    def test_invalid_pom_warns_without_hiding_other_ecosystems(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text(
                '<!DOCTYPE project [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
                "<project><dependencies>&x;</dependencies></project>",
                encoding="utf-8",
            )
            (root / "go.mod").write_text(
                "module example.com/app\nrequire example.com/dependency v1.0.0\n",
                encoding="utf-8",
            )
            report = scan(root)
            self.assertEqual(report["totals"], {"Go": 1})
            self.assertEqual(len(report["warnings"]), 1)
            self.assertIn("pom.xml", report["warnings"][0])
            self.assertIn("DTD", report["warnings"][0])
            self.assertEqual([item["path"] for item in report["manifests"]], ["go.mod"])


if __name__ == "__main__":
    unittest.main()
