"""Bound direct requirements-filename matching on untrusted long inputs."""

import unittest

from devpilot.requirements_names import (
    MAX_REQUIREMENTS_FILENAME_CHARS,
    is_requirements_manifest,
)


class RequirementsFilenameLengthTests(unittest.TestCase):
    def test_255_character_manifest_is_still_recognized(self):
        prefix = 'requirements-'
        suffix = '.txt'
        name = prefix + 'a' * (MAX_REQUIREMENTS_FILENAME_CHARS - len(prefix) - len(suffix)) + suffix
        self.assertEqual(len(name), 255)
        self.assertTrue(is_requirements_manifest(name))

    def test_overlong_well_formed_manifest_is_rejected(self):
        name = 'requirements-' + 'a' * 239 + '.txt'
        self.assertEqual(len(name), 256)
        self.assertFalse(is_requirements_manifest(name))

    def test_extremely_long_invalid_qualifiers_are_bounded(self):
        self.assertFalse(is_requirements_manifest('requirements-' + 'a-' * 100_000 + '!.txt'))

    def test_non_string_input_is_rejected(self):
        self.assertFalse(is_requirements_manifest(None))


if __name__ == '__main__':
    unittest.main()
