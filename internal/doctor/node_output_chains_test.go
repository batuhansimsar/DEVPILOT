package doctor

import "testing"

func TestNodeTestOutputOnlyShellChains(t *testing.T) {
	cases := []struct {
		name, script string
		runnable bool
	}{
		{"and chain", `echo preparing && echo done`, false},
		{"or chain", `echo unavailable || printf 'try again'`, false},
		{"mixed output operators", `echo 'a && b'; printf '%s' done || echo skipped`, false},
		{"single pipe runs command", `echo hello | node --test`, true},
		{"single ampersand backgrounds command", `echo hello & node --test`, true},
		{"real test after output", `echo preparing && node --test`, true},
		{"real test before output", `npm run jest || echo failure`, true},
		{"substitution remains runnable", `echo "$(node --test)" && echo done`, true},
		{"nested operator rejected", `echo ready &&& node --test`, true},
		{"quoted operator literal", `echo "a || b" && printf 'ok'`, false},
		{"pipeline with output filter", `echo hello | cat`, true},
		{"semicolon only", `printf done; echo okay`, false},
		{"trailing semicolon", `echo ready && printf done;`, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasRunnableNodeTestScript(tc.script); got != tc.runnable {
				t.Fatalf("hasRunnableNodeTestScript(%q) = %t, want %t", tc.script, got, tc.runnable)
			}
		})
	}
}
