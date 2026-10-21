package doctor

import "testing"

func TestHasPytestINISection(t *testing.T) {
	cases := []struct {
		name, content, section string
		want                   bool
	}{
		{"tox pytest", "[tox]\nenv_list = py\n[pytest]\naddopts = -q\n", "[pytest]", true},
		{"setup cfg pytest", "[metadata]\nname = app\n[tool:pytest]\ntestpaths = tests\n", "[tool:pytest]", true},
		{"BOM", "\ufeff[pytest]\n", "[pytest]", true},
		{"CRLF", "[pytest]\r\n", "[pytest]", true},
		{"trailing spaces", "[pytest] \t\n", "[pytest]", true},
		{"unrelated tox", "[tox]\nenv_list = py\n", "[pytest]", false},
		{"commented", "# [pytest]\n;[pytest]\n", "[pytest]", false},
		{"indented multiline option", "[tox]\ndescription =\n  [pytest]\n", "[pytest]", false},
		{"section suffix", "[pytest-extra]\n", "[pytest]", false},
		{"inline trailing comment", "[pytest] # note\n", "[pytest]", false},
		{"mismatched section", "[pytest]\n", "[tool:pytest]", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasPytestINISection([]byte(tc.content), tc.section); got != tc.want {
				t.Fatalf("hasPytestINISection() = %t; want %t", got, tc.want)
			}
		})
	}
}
