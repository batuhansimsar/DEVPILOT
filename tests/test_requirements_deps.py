"""Regression tests for pip requirement parsing and credential privacy."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.requirements_deps import parse_requirements_dependencies
from devpilot.deps import scan


class RequirementsParserTests(unittest.TestCase):
    def test_valid_pins_extras_markers_and_direct_references(self):
        text = ('requests>=2 # required\n'
                'Fancy_Pkg[http] # extras\n'
                'pydantic; python_version >= "3.10"\n'
                'Example-Pkg @ https://user:secret@example.org/a.whl#sha256=abc\n'
                '--index-url https://user:private@example.org/simple\n'
                'git+https://example.org/repo.git\n')
        self.assertEqual(parse_requirements_dependencies(text),
                         ['example-pkg', 'fancy-pkg', 'pydantic', 'requests'])
        self.assertNotIn('secret', str(parse_requirements_dependencies(text)))

    def test_malformed_declarations_are_not_reported_as_dependencies(self):
        text = ('requests @\nrequests >\nrequests!!!\n'
                'broken[invalid extra]\nrequests==\n'
                'good==1.2\n')
        self.assertEqual(parse_requirements_dependencies(text), ['good'])

    def test_pip_hash_options_and_line_continuation(self):
        text = ('requests==2.0 --hash=sha256:abc123 --hash=sha512:aa11\n'
                'urllib3==2.2 \\\n'
                '    --hash=sha256:bb22\n')
        self.assertEqual(parse_requirements_dependencies(text), ['requests', 'urllib3'])

    def test_invalid_hash_or_option_does_not_create_fake_package(self):
        text = 'fake==1.0 --hash=sha256:NOTHEX\nother --trusted-host evil.test\n'
        self.assertEqual(parse_requirements_dependencies(text), [])

    def test_scan_reports_only_valid_names_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'requirements.txt').write_text(
                'valid==1\ninvalid!!!\n'
                'private_ref @ https://user:secret@example.invalid/lib.whl\n'
                'hash-pkg==2 --hash=sha256:abc123\n',
                encoding='utf-8',
            )
            report = scan(directory)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['manifests'][0]['groups']['requirements'],
                         ['hash-pkg', 'private-ref', 'valid'])
        self.assertNotIn('secret', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
