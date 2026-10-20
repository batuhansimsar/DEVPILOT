package doctor

import "testing"

func TestParseGitHeadBranch(t *testing.T) {
	cases := []struct {
		name string
		head string
		want string
		ok   bool
	}{
		{"main", "ref: refs/heads/main\n", "main", true},
		{"nested branch", "ref: refs/heads/feature/auth\r\n", "feature/auth", true},
		{"unicode branch", "ref: refs/heads/fix/日本語\n", "fix/日本語", true},
		{"missing branch", "ref: refs/heads/\n", "", false},
		{"detached head", "0123456789abcdef0123456789abcdef01234567\n", "", false},
		{"terminal escape", "ref: refs/heads/\x1b[31mspoof\n", "", false},
		{"carriage return injection", "ref: refs/heads/main\rspoof\n", "", false},
		{"line injection", "ref: refs/heads/main\nspoof\n", "", false},
		{"bidi override", "ref: refs/heads/main\u202espoof\n", "", false},
		{"zero width joiner", "ref: refs/heads/main\u200dspoof\n", "", false},
		{"unicode separator", "ref: refs/heads/main\u2028spoof\n", "", false},
		{"space", "ref: refs/heads/bad name\n", "", false},
		{"trailing space", "ref: refs/heads/main \n", "", false},
		{"backslash", "ref: refs/heads/bad\\name\n", "", false},
		{"non UTF8", "ref: refs/heads/\xff\n", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, ok := parseGitHeadBranch([]byte(tc.head))
			if got != tc.want || ok != tc.ok {
				t.Fatalf("parseGitHeadBranch(%q) = (%q, %v), want (%q, %v)", tc.head, got, ok, tc.want, tc.ok)
			}
		})
	}
}
