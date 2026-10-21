import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class PEP508DirectReferenceTests(unittest.TestCase):
    def test_named_direct_references_are_inventoried_without_leaking_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "requirements.txt").write_text(
                "flask>=3\n"
                "Fancy_Pkg[extra] @ https://user:secret@downloads.example.test/path/pkg.whl\n"
                "another-lib @ git+https://user:token@git.example.test/thing.git\n"
                "git+https://elsewhere.example.test/unnamed.git\n"
                "--extra-index-url https://user:private@registry.example.test/simple\n"
            )
            result = scan(directory)
            self.assertEqual(result["manifests"][0]["groups"]["requirements"],
                             ["another-lib", "fancy-pkg", "flask"])
            # The canonical macOS temp path contains '/private'; it is not a URL leak.
            serialized = json.dumps({key: value for key, value in result.items() if key != 'root'})
            for secret in ("secret", "token", "private", "downloads.example.test", "git.example.test"):
                self.assertNotIn(secret, serialized)

    def test_named_direct_ref_without_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "requirements.txt").write_text(
                "my_pkg@https://example.test/archive.whl\ninvalid_ref@\n"
            )
            self.assertEqual(scan(directory)["totals"], {"Python": 1})


if __name__ == "__main__":
    unittest.main()
