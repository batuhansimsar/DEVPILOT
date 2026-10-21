"""Infrastructure, schema, and DSL files appear in language inventory."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project


class DeclarativeSourceLanguageTests(unittest.TestCase):
    def test_declarative_source_extensions_are_classified(self):
        examples = {
            'infra/main.tf': 'Terraform',
            'infra/staging.TFVARS': 'Terraform',
            'schema/messages.proto': 'Protocol Buffers',
            'api/public.GRAPHQL': 'GraphQL',
            'api/internal.gql': 'GraphQL',
            'db/schema.prisma': 'Prisma',
            'nix/default.nix': 'Nix',
            'validation/policy.cue': 'CUE',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in examples:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('example', encoding='utf-8')
            (root / 'notes.txt').write_text('not source', encoding='utf-8')
            result = analyze_project(root)
            self.assertFalse(result['truncated'])
            self.assertEqual(result['file_count'], len(examples) + 1)
            self.assertEqual(result['languages'], {
                'Terraform': 2, 'GraphQL': 2, 'Protocol Buffers': 1,
                'Prisma': 1, 'Nix': 1, 'CUE': 1,
            })


if __name__ == '__main__':
    unittest.main()
