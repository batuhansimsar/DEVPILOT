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
		{"noop-colon", ":", false},
		{"noop-true", "true", false},
		{"noop-false", "false", false},
		{"noop-exit", "exit", false},
		{"noop-exit-zero", " exit 0 ", false},
		{"noop-with-semicolon", "true;", false},
		{"compound-with-real-test", "true && node --test", true},
		{"exit-nonzero", "exit 1", false},
		{"exit-with-code", "exit 42;", false},
		{"exit-with-whitespace", "exit  0 ;", false},
		{"exit-then-real-test", "exit 1 || node --test", true},
		{"real-test-with-semicolon", "node --test;", true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasRunnableNodeTestScript(tc.script); got != tc.want {
				t.Fatalf("hasRunnableNodeTestScript(%q) = %v, want %v", tc.script, got, tc.want)
			}
		})
	}
}
