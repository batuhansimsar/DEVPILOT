package doctor

import "testing"

func TestNodeOutputAndExitIsNotTestSuite(t *testing.T) {
	cases := []struct {
		name   string
		script string
		want   bool
	}{
		{"echo then success", `echo "Tests are not configured" && exit 0`, false},
		{"printf then success", `printf 'No tests' && exit 0`, false},
		{"unquoted message", `echo no tests yet && exit 0;`, false},
		{"whitespace", " echo missing tests  &&  exit  0 ; ", false},
		{"actual test fallback", `echo "No tests" && exit 1 || node --test`, true},
		{"actual test later", `echo "No tests" && exit 0; node --test`, true},
		{"actual test before exit", `echo "No tests" && node --test && exit 0`, true},
		{"command substitution", `echo "$(node --test)" && exit 0`, true},
		{"backtick substitution", "echo `node --test` && exit 0", true},
		{"redirected output", `echo no tests > output.log && exit 0`, true},
		{"empty message", `echo && exit 0`, false},
		{"nonzero custom failure preserved", `echo custom diagnostic && exit 2`, true},
		{"exit shell expansion", `echo no tests && exit "$?"`, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasRunnableNodeTestScript(tc.script); got != tc.want {
				t.Errorf("hasRunnableNodeTestScript(%q) = %v; want %v", tc.script, got, tc.want)
			}
		})
	}
}
