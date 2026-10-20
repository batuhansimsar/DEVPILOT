import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import main, scan


class DependencyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_node_groups_and_no_secret_values(self):
        (self.root / "package.json").write_text(json.dumps({
            "dependencies": {"axios": "https://user:token@example.test/file", "react": "^18"},
            "devDependencies": {"vitest": "*"}}))
        report = scan(self.root)
        self.assertEqual(report["totals"]["Node.js"], 3)
        self.assertNotIn("token", json.dumps(report))
        self.assertEqual(report["manifests"][0]["groups"]["dependencies"], ["axios", "react"])

    def test_python_requirements_skip_options_and_urls(self):
        (self.root / "requirements.txt").write_text(
            "requests>=2\n# comment\n--index-url https://user:token@host/\n-r private.txt\nFlask==3.0\ngit+https://host/repo\n")
        items = scan(self.root)["manifests"][0]["groups"]["requirements"]
        self.assertEqual(items, ["flask", "requests"])

    def test_go_require_multiline_and_single(self):
        (self.root / "go.mod").write_text("module example.org/x\nrequire (\n example.org/a v1.2.3\n example.com/b v0.2.0 // indirect\n)\nrequire example.net/c v1.0.0\n")
        self.assertEqual(scan(self.root)["totals"]["Go"], 3)

    def test_cargo_groups(self):
        (self.root / "Cargo.toml").write_text('[dependencies]\nserde = "1"\n[dev-dependencies]\ntokio = "1"\n')
        self.assertEqual(scan(self.root)["totals"]["Rust"], 2)

    def test_cargo_table_form_dependencies_and_target_groups(self):
        (self.root / "Cargo.toml").write_text(
            '[dependencies.serde]\nversion = "1"\n'
            '[dev-dependencies.pretty_assertions]\nversion = "1"\n'
            '[workspace.dependencies.anyhow]\nversion = "1"\n'
            "[target.'cfg(unix)'.build-dependencies.cc]\nversion = \"1\"\n"
            "[target.'cfg(windows)'.dependencies]\nwinapi = \"1\"\n"
        )
        groups = scan(self.root)["manifests"][0]["groups"]
        self.assertEqual(groups, {
            "dependencies": ["anyhow", "serde", "winapi"],
            "dev-dependencies": ["pretty_assertions"],
            "build-dependencies": ["cc"],
        })

    def test_cargo_metadata_dependencies_are_not_packages(self):
        (self.root / "Cargo.toml").write_text(
            '[package.metadata.dependencies]\nnot_a_dependency = "1"\n'
            '[package.metadata.dependencies.fake]\nversion = "1"\n'
            '[features]\nfull = ["dep:serde"]\n'
        )
        self.assertEqual(scan(self.root)["manifests"][0]["groups"], {})
        self.assertEqual(scan(self.root)["totals"]["Rust"], 0)

    def test_dotnet_references(self):
        (self.root / "app.csproj").write_text('<Project><ItemGroup><PackageReference Include="MediatR" Version="1"/><PackageReference Update="Serilog"/></ItemGroup></Project>')
        self.assertEqual(scan(self.root)["manifests"][0]["groups"]["PackageReference"], ["MediatR", "Serilog"])

    def test_invalid_json_warning_and_cli_status(self):
        (self.root / "package.json").write_text('{bad')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--path", str(self.root), "--json"]), 1)
        self.assertTrue(json.loads(output.getvalue())["warnings"])

    def test_does_not_follow_symlinked_directories(self):
        outside = self.root / "real"
        outside.mkdir()
        (outside / "go.mod").write_text("require example.org/a v1.0.0")
        try:
            (self.root / "linked").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink unsupported")
        self.assertEqual(len(scan(self.root)["manifests"]), 1)

    def test_rejects_xml_entities(self):
        (self.root / "bad.csproj").write_text('<!DOCTYPE foo [<!ENTITY x "secret">]><Project>&x;</Project>')
        self.assertIn("DTD", scan(self.root)["warnings"][0])

    def test_ignores_node_modules(self):
        folder = self.root / "node_modules" / "private"
        folder.mkdir(parents=True)
        (folder / "package.json").write_text('{bad')
        self.assertEqual(scan(self.root)["manifests"], [])


if __name__ == "__main__":
    unittest.main()
