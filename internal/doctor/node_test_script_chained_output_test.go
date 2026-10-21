package doctor

import "testing"

func TestNodeTestScriptChainedOutputCommands(t *testing.T) {
	for _, tc := range []struct {
		name, script string
		runnable bool
	}{
		{"two echoes", "echo \"starting\"; echo \"no tests\"", false},
		{"echo followed by printf", "echo \"starting\" ; printf 'not configured'", false},
		{"three output statements", "echo first; printf '%s' second; echo third;", false},
		{"quoted semicolons", "echo \"not; a; test\"; printf '%s; %s' one two", false},
		{"single trailing semicolon", "echo status;", false},
		{"space after trailing semicolon", "echo status;  ", false},
		{"double semicolon invalid", "echo status;;", true},
		{"leading empty statement", "; echo status", true},
		{"real test after echo", "echo preparing; node --test", true},
		{"real test after printf", "printf 'ready'; vitest run", true},
		{"command substitution", "echo ready; printf \"$(node --test)\"", true},
		{"command chaining", "echo ready && printf 'pending'", true},
		{"pipe to real tests", "echo ready | node --test", true},
		{"shell redirect", "echo ready; printf 'pending' > log.txt", true},
		{"quoted line break with test", "echo ready;\nnode --test", true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasRunnableNodeTestScript(tc.script); got != tc.runnable {
				t.Fatalf("hasRunnableNodeTestScript(%q) = %v, want %v", tc.script, got, tc.runnable)
			}
		})
	}
}
