"""Regression coverage for OpenSSH FIDO/U2F private-key filename detection."""
import unittest
from devpilot.secret_audit import classify


class OpenSSHSecurityKeyTests(unittest.TestCase):
    def test_ssh_security_key_private_files_are_flagged(self):
        for name in (
            'id_ecdsa_sk', 'id_ed25519_sk',
            'users/dev/.ssh/id_ecdsa_sk', '.ssh/id_ed25519_sk',
            'windows\\.ssh\\ID_ED25519_SK',
            '.ssh/id_ed25519_sk.bak',
        ):
            with self.subTest(name=name):
                self.assertEqual(classify(name), 'potential credential file')

    def test_public_key_and_example_files_are_not_flagged(self):
        for name in (
            'id_ecdsa_sk.pub', 'id_ed25519_sk.pub',
            '.ssh/id_ecdsa_sk.example', '.ssh/id_ed25519_sk.sample',
            'docs/how-to-create-id_ed25519_sk.txt',
        ):
            with self.subTest(name=name):
                self.assertIsNone(classify(name))


if __name__ == '__main__':
    unittest.main()
