package doctor

import "testing"

func TestHasPytestINISectionInlineComments(t *testing.T) {
	cases := []struct {
		name, data, section string
		want                bool
	}{
		{"tox hash comment", "[tox]\nenv_list = py\n[pytest] # pytest options\naddopts = -q\n", "[pytest]", true},
		{"setup semicolon comment", "[tool:pytest] ; options\r\n", "[tool:pytest]", true},
		{"adjacent comment", "[pytest]# note\n", "[pytest]", true},
		{"header suffix", "[pytest] invalid\n", "[pytest]", false},
		{"similar section", "[pytest-extra] # comment\n", "[pytest]", false},
		{"continuation line", "[tox]\ndescription =\n  [pytest] # fake\n", "[pytest]", false},
		{"commented out", "; [pytest] # fake\n", "[pytest]", false},
		{"malformed suffix", "[pytest] x # comment\n", "[pytest]", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasPytestINISection([]byte(tc.data), tc.section); got != tc.want {
				t.Fatalf("got %t, want %t", got, tc.want)
			}
		})
	}
}
