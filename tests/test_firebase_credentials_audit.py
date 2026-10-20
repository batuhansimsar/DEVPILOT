"""Firebase private key filename detection should be conservative and read-only."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.firebase_credentials import is_firebase_service_account_key
from devpilot.secret_audit import audit, classify


class FirebaseCredentialTests(unittest.TestCase):
    def test_known_private_key_names_are_detected_by_both_auditors(self):
        names = (
            'serviceAccountKey.json', 'credentials/service_account_key.json',
            'service-account-key.json.bak',
            'app/my-project-firebase-adminsdk-a1b2c-0123456789abcdef.json',
            'APP\\FIREBASE-ADMINSDK-A1B2C-0123456789.JSON.old',
        )
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))
                self.assertIsNotNone(classify(name))

    def test_unrelated_firebase_manifests_and_templates_are_ignored(self):
        names = (
            'firebase.json', 'google-services.json', 'firebase-adminsdk-guide.json',
            'firebase-adminsdk-ab123-short.json',
            'serviceAccountKey.json.example',
            'service_account_key.json.sample',
            'project-firebase-adminsdk-abc12-0123456789.json.template',
        )
        for name in names:
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))
                self.assertIsNone(classify(name))

    def test_helper_rejects_non_strings_and_malformed_names(self):
        self.assertFalse(is_firebase_service_account_key(None))
        self.assertFalse(is_firebase_service_account_key('firebase-adminsdk-abc12-123.json'))
        self.assertTrue(is_firebase_service_account_key('ServiceAccountKey.JSON'))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_git_index_audit_reports_tracked_keys_without_reading_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            tracked = (
                'serviceAccountKey.json',
                'config/demo-firebase-adminsdk-abc12-0123456789.json',
                'google-services.json',
                'serviceAccountKey.json.example',
            )
            for name in (*tracked, 'untracked-firebase-adminsdk-abc12-0123456789.json'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('DO_NOT_ECHO_CREDENTIAL_MATERIAL', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *tracked], cwd=root, check=True)
            simple = audit_tracked_files(root)
            detailed = audit(root)
        expected = [
            'config/demo-firebase-adminsdk-abc12-0123456789.json',
            'serviceAccountKey.json',
        ]
        self.assertNotIn('error', simple)
        self.assertEqual(simple['tracked_files'], 4)
        self.assertEqual(simple['candidates'], expected)
        self.assertEqual(sorted(finding['path'] for finding in detailed['findings']), expected)
        self.assertNotIn('DO_NOT_ECHO', str(simple))
        self.assertNotIn('DO_NOT_ECHO', str(detailed))


if __name__ == '__main__':
    unittest.main()
