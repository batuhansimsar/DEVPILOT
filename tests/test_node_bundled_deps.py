"""npm bundled dependencies are included in the read-only inventory."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.node_deps import parse_node_dependency_groups


class BundledDependencyTests(unittest.TestCase):
    def test_both_npm_aliases_are_supported(self):
        for alias in ("bundleDependencies", "bundledDependencies"):
            with self.subTest(alias=alias):
                self.assertEqual(parse_node_dependency_groups({
                    alias: ["@scope/pkg", "react", "react"],
                }), {"bundleDependencies": ["@scope/pkg", "react"]})

    def test_true_bundles_production_dependencies_only(self):
        data = {"dependencies": {"react": "https://user:secret@host.test/x"},
                "devDependencies": {"vitest": "^2"}, "bundleDependencies": True}
        result = parse_node_dependency_groups(data)
        self.assertEqual(result["bundleDependencies"], ["react"])
        self.assertNotIn("secret", str(result))
        self.assertNotIn("vitest", str(result["bundleDependencies"]))

    def test_false_or_empty_list_does_not_add_group(self):
        for value in (False, []):
            with self.subTest(value=value):
                self.assertEqual(parse_node_dependency_groups({"bundleDependencies": value}), {})

    def test_rejects_invalid_bundled_values_without_echoing_secrets(self):
        for value in (None, 12, "react", {"token": "secret"},
                      ["https://user:secret@host.test/pkg"], ["ok", None]):
            with self.subTest(value=value), self.assertRaises(ValueError) as error:
                parse_node_dependency_groups({"bundleDependencies": value})
            self.assertNotIn("secret", str(error.exception))
            self.assertNotIn("https", str(error.exception))

    def test_case_conflicts_are_rejected_without_exposing_values(self):
        with self.assertRaisesRegex(ValueError, "duplicate case-insensitive package names"):
            parse_node_dependency_groups({"bundledDependencies": ["React", "react"]})

    def test_rejects_ambiguous_aliases(self):
        with self.assertRaisesRegex(ValueError, "both bundled dependency aliases"):
            parse_node_dependency_groups({"bundleDependencies": ["a"],
                                          "bundledDependencies": ["b"]})

    def test_scanner_integration(self):
        from devpilot.deps import scan
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "package.json").write_text(json.dumps({
                "dependencies": {"react": "^19"},
                "bundledDependencies": ["react", "@scope/pkg"],
            }), encoding="utf-8")
            result = scan(temp)
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["totals"], {"Node.js": 3})
        self.assertEqual(result["manifests"][0]["groups"], {
            "dependencies": ["react"],
            "bundleDependencies": ["@scope/pkg", "react"],
        })


if __name__ == "__main__":
    unittest.main()
