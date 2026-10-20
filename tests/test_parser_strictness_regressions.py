"""Keep parser boundaries strict across direct calls and filename discovery."""

import json
import unittest

from devpilot.json_numbers import parse_finite_json_float
from devpilot.requirements_names import is_requirements_manifest


class ParserStrictnessRegressionTests(unittest.TestCase):
    def test_json_number_parser_rejects_python_float_extensions(self):
        for token in ('+1', '.5', '-.5', '1.', '01', '-01', '1_000',
                      ' 1', '1 ', '\t1', '1e', '1e+', '0x1', 'nan'):
            with self.subTest(token=token):
                with self.assertRaisesRegex(ValueError, '^invalid JSON number$'):
                    parse_finite_json_float(token)

    def test_json_number_parser_accepts_valid_finite_tokens(self):
        for token, expected in (('0', 0.0), ('-0', -0.0), ('1', 1.0),
                                ('0.5', .5), ('1e+2', 100.0),
                                ('1E-2', .01), ('1.0e0', 1.0)):
            with self.subTest(token=token):
                self.assertEqual(parse_finite_json_float(token), expected)

    def test_json_number_parser_does_not_echo_sensitive_input(self):
        with self.assertRaisesRegex(ValueError, '^invalid JSON number$') as raised:
            parse_finite_json_float('1 # private-token=secret')
        self.assertNotIn('secret', str(raised.exception))
        with self.assertRaisesRegex(ValueError, '^non-finite JSON number$'):
            json.loads('{"metric": 1e99999}', parse_float=parse_finite_json_float)

    def test_requirements_names_handle_ascii_case_consistently(self):
        for name in ('Requirements.TXT', 'requirements.IN', 'REQUIREMENTS-DEV.In',
                     'dev-Requirements.TXT', 'requirements_Test.In'):
            with self.subTest(name=name):
                self.assertTrue(is_requirements_manifest(name))

    def test_requirements_names_reject_lookalikes_and_double_extensions(self):
        for name in ('requirKments.txt', 'requirementſ.txt', 'requirements-Δ.txt',
                     'requirements.txt.txt', 'requirements.TXT.IN',
                     'requirements.IN.txt', 'requirements.in.IN',
                     'requirementsnotes.txt', 'requirements-.txt',
                     '../requirements.txt'):
            with self.subTest(name=name):
                self.assertFalse(is_requirements_manifest(name))


if __name__ == '__main__':
    unittest.main()
