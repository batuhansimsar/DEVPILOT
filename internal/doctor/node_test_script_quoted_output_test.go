package doctor

import "testing"

func TestNodeTestScriptQuotedShellMetacharacters(t *testing.T) {
	cases := []struct {
		name, script string
		runnable bool
	}{
		{"pipe in double quotes", "echo \"Test results | pending\"", false},
		{"ampersand in double quotes", "echo \"Build && test\"", false},
		{"semicolon in single quotes", "printf '%s; %s' disabled disabled", false},
		{"redirection in single quotes", "echo '<tests unavailable>'", false},
		{"backticks in single quotes", "echo '`node --test`'", false},
		{"dollar expansion in single quotes", "echo '$(node --test)'", false},
		{"multiple quoted operators", "printf '&& | ; <> $()'", false},
		{"quoted operators with terminal semicolon", "echo \"no tests | yet\";", false},
		{"command substitution in double quotes", "echo \"$(node --test)\"", true},
		{"backtick substitution in double quotes", "echo \"`node --test`\"", true},
		{"dollar variable in double quotes", "echo \"$TEST_COMMAND\"", true},
		{"escape in double quotes", "echo \"foo\\bar\"", true},
		{"unterminated single quote", "echo 'missing", true},
		{"unterminated double quote", "echo \"missing", true},
		{"real test after quoted output", "echo \"no tests | yet\" && node --test", true},
		{"real test after semicolon", "echo \"none; yet\"; node --test", true},
		{"pipeline after quoted output", "echo \"none | yet\" | node --test", true},
		{"actual redirect after quoted output", "echo \"none > yet\" > output", true},
		{"multiline script", "echo 'none | yet'\nnode --test", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasRunnableNodeTestScript(tc.script); got != tc.runnable {
				t.Fatalf("hasRunnableNodeTestScript(%q) = %t, want %t", tc.script, got, tc.runnable)
			}
		})
	}
}
