"""Regression coverage for mixed-case .NET project manifest extensions."""

import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class DotnetManifestCaseTests(unittest.TestCase):
    def test_mixed_case_project_extensions_are_scanned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, package in (
                ('Api.CSPROJ', 'Serilog'),
                ('Worker.FsProj', 'FSharp.Core'),
                ('Legacy.VBPROJ', 'Newtonsoft.Json'),
            ):
                (root / name).write_text(
                    f'<Project><ItemGroup><PackageReference Include="{package}" /></ItemGroup></Project>',
                    encoding='utf-8',
                )

            report = scan(root)
            self.assertFalse(report['warnings'])
            self.assertEqual(report['totals'], {'.NET': 3})
            self.assertEqual(
                {item['path']: item['groups']['PackageReference'] for item in report['manifests']},
                {
                    'Api.CSPROJ': ['Serilog'],
                    'Worker.FsProj': ['FSharp.Core'],
                    'Legacy.VBPROJ': ['Newtonsoft.Json'],
                },
            )

    def test_mixed_case_xml_still_refuses_doctype(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'Risk.CSPROJ').write_text(
                '<!DOCTYPE foo [<!ENTITY secret SYSTEM "file:///etc/passwd">]><Project />',
                encoding='utf-8',
            )
            report = scan(root)
            self.assertEqual(report['manifests'], [])
            self.assertEqual(len(report['warnings']), 1)
            self.assertIn('DTD', report['warnings'][0])


if __name__ == '__main__':
    unittest.main()
