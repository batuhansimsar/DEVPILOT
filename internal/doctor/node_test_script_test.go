package doctor

import "testing"

func TestHasRunnableNodeTestScript(t *testing.T) {
	for _, tc := range []struct {
		name   string
		script string
		want   bool
	}{
		{"empty", "", false},
		{"whitespace", " \t\n ", false},
		{"npm-init-default", `echo "Error: no test specified" && exit 1`, false},
		{"npm-init-case-insensitive", `ECHO 'NO TEST SPECIFIED' && EXIT 1`, false},
		{"npm-init-unquoted", `echo Error: no test specified && exit 1`, false},
		{"npm-init-semicolon", `echo 'no test specified' && exit 1;`, false},
		{"vitest", "vitest run", true},
		{"node-test", "node --test", true},
		{"echo-before-real-test", `echo "running tests" && jest`, true},
		{"documentary-message-not-placeholder", `node test.js --message="no test specified"`, true},
		{"fallback-after-default", `echo "Error: no test specified" && exit 1 || vitest run`, true},
		{"real-test-before-exit", `echo "no test specified" && jest && exit 1`, true},
		{"subsequent-script", `echo "Error: no test specified" && exit 1; npm test`, true},
		{"similar-but-custom-message", `echo "no test specified for this environment" && exit 1`, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasRunnableNodeTestScript(tc.script); got != tc.want {
				t.Fatalf("hasRunnableNodeTestScript(%q) = %v, want %v", tc.script, got, tc.want)
			}
		})
	}
}
