package doctor

import "testing"

func TestNodeTestScriptRejectsOutputOnly(t *testing.T) {
	for _, tc := range []struct {
		script string
		want   bool
	}{
		{`echo "No tests configured"`, false},
		{`printf 'No tests yet'`, false},
		{`echo`, false},
		{`printf "Tests run externally";`, false},
		{`echo "Starting tests" && vitest run`, true},
		{`echo "$(node --test)"`, true},
		{"echo ready\nnode --test", true},
		{`echo ready | node --test`, true},
		{`echo ready; node --test`, true},
		{`echo ready > ./log.txt`, true},
		{`printf '%s' "$(npm test)"`, true},
	} {
		t.Run(tc.script, func(t *testing.T) {
			if got := hasRunnableNodeTestScript(tc.script); got != tc.want {
				t.Fatalf("hasRunnableNodeTestScript(%q) = %v, want %v", tc.script, got, tc.want)
			}
		})
	}
}
