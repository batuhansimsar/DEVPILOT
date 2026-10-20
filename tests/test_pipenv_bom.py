"""Direct Pipfile.lock parsing matches scanner UTF-8-SIG behavior."""

import unittest

from devpilot.pipenv_deps import parse_pipfile_lock


class PipenvBOMTests(unittest.TestCase):
    def test_accepts_one_leading_bom_and_keeps_metadata_private(self):
        content = ('\ufeff{"_meta":{"sources":[{"url":"https://user:secret@example.test"}]},'
                   '"default":{"My_Pkg":{"version":"==1"}},'
                   '"develop":{"pytest":{"version":"==8"}}}')
        result = parse_pipfile_lock(content)
        self.assertEqual(result, {'default': ['my-pkg'], 'develop': ['pytest']})
        self.assertNotIn('secret', str(result))

    def test_bom_cannot_mask_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, 'duplicate object keys'):
            parse_pipfile_lock('\ufeff{"default":{"one":{},"one":{}}}')

    def test_bom_cannot_mask_nonfinite_values(self):
        with self.assertRaisesRegex(ValueError, 'finite JSON numbers'):
            parse_pipfile_lock('\ufeff{"x":1e1000}')

    def test_only_one_initial_bom_is_accepted(self):
        for content in ('\ufeff\ufeff{}', '{\ufeff}', '{}\ufeff'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_pipfile_lock(content)


if __name__ == '__main__':
    unittest.main()
