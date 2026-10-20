"""Service-account key aliases are recognized without scanning file contents."""

import unittest

from devpilot.firebase_credentials import is_firebase_service_account_key


class FirebaseCredentialAliasTests(unittest.TestCase):
    def test_common_credential_export_aliases_are_detected(self):
        for filename in (
            'serviceAccount.json',
            'Firebase-Credentials.json',
            'firebase_credentials.json',
            'firebaseCredentials.json',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_firebase_service_account_key(filename))

    def test_unrelated_configs_and_templates_remain_ignored(self):
        for filename in (
            'firebase.json',
            'firebase-config.json',
            'google-services.json',
            'serviceAccount.json.example',
            'firebase-credentials.json.sample',
            'firebase_credentials.json.template',
            'not-firebase-credentials.json',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_firebase_service_account_key(filename))

    def test_handles_nonstring_inputs(self):
        for value in (None, 0, ['firebase_credentials.json']):
            with self.subTest(value=value):
                self.assertFalse(is_firebase_service_account_key(value))


if __name__ == '__main__':
    unittest.main()
