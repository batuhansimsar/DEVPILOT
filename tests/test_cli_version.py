"""Version output tracks package metadata and works from source trees."""

import unittest
from importlib import metadata
from unittest.mock import patch

from devpilot.version import cli_version


class CLIVersionTests(unittest.TestCase):
    def test_installed_package_version_is_reported(self):
        with patch('devpilot.version.metadata.version', return_value='2.7.3') as lookup:
            self.assertEqual(cli_version(), 'devpilot 2.7.3')
        lookup.assert_called_once_with('devpilot-cli')

    def test_source_checkout_uses_package_version_constant(self):
        with patch('devpilot.version.metadata.version', side_effect=metadata.PackageNotFoundError):
            with patch('devpilot.version.__version__', '0.1.0'):
                self.assertEqual(cli_version(), 'devpilot 0.1.0')


if __name__ == '__main__':
    unittest.main()
