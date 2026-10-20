"""Common Firebase service-account export names must not bypass filename audits."""

import unittest

from devpilot.firebase_credentials import is_firebase_service_account_key


class FirebaseServiceAccountAliasTests(unittest.TestCase):
    def test_common_service_account_export_names(self):
        for filename in (
            'firebase-service-account.json',
            'firebase_service_account.json',
            'firebaseServiceAccount.json',
            'firebase-service-account-key.json',
            'firebase_service_account_key.json',
            'firebaseServiceAccountKey.json',
            'FIREBASE-SERVICE-ACCOUNT-KEY.JSON',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_firebase_service_account_key(filename))

    def test_do_not_treat_client_config_or_templates_as_private_keys(self):
        for filename in (
            'firebase.json',
            'firebase-config.json',
            'google-services.json',
            'firebase-service-account.json.example',
            'firebase-service-account-key.json.sample',
            'firebaseServiceAccountKey.json.template',
            'firebase-service-account-custom.json',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_firebase_service_account_key(filename))


if __name__ == '__main__':
    unittest.main()
