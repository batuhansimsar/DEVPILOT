"""Track credential-bearing .NET deployment profiles without false positives."""

import unittest

from devpilot.publish_profiles import is_publish_profile
from devpilot.secret_audit import classify
from devpilot.audit import _potential_secret


class PublishProfileAuditTests(unittest.TestCase):
    def test_both_auditors_detect_publish_profile_credentials(self):
        paths = (
            'Properties/PublishProfiles/Production.pubxml',
            'src/MyApp/Properties/PublishProfiles/Prod.pubxml.user',
            'src\\MyApp\\Properties\\PublishProfiles\\Prod.pubxml.user',
            'PROPERTIES/PUBLISHPROFILES/STAGING.PUBXML',
            'Properties/PublishProfiles/Production.pubxml.bak',
            'Properties/PublishProfiles/Production.pubxml.user.old',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential .NET publish profile credentials')

    def test_unrelated_files_and_templates_are_not_flagged(self):
        for path in (
            'src/Settings.pubxml',
            'Properties/Other/Production.pubxml',
            'docs/PublishProfiles/Production.pubxml',
            'Properties/PublishProfiles/README.md',
            'Properties/PublishProfiles/Production.pubxml.example',
            'Properties/PublishProfiles/Production.pubxml.user.template',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    def test_filename_predicate_rejects_incomplete_paths(self):
        for parts in ((), ('prod.pubxml',), ('publishprofiles', 'prod.pubxml')):
            with self.subTest(parts=parts):
                self.assertFalse(is_publish_profile(parts))


if __name__ == '__main__':
    unittest.main()
