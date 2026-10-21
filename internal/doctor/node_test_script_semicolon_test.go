package doctor

import "testing"

func TestNodeTestScriptSemicolonPlaceholder(t *testing.T) {
	tests := []struct {
		name, script string
		want bool
	}{
		{"single quoted placeholder", `echo 'Error: no test specified'; exit 1`, false},
		{"double quoted placeholder", `echo "Error: no test specified" ; exit 1;`, false},
		{"unquoted placeholder", `echo no test specified; exit 1`, false},
		{"existing npm default", `echo "Error: no test specified" && exit 1`, false},
		{"real test after semicolon", `echo 'Error: no test specified'; exit 1; node --test`, true},
		{"fallback real test", `echo 'Error: no test specified'; exit 1 || node --test`, true},
		{"different message", `echo 'no test specified here'; exit 1`, true},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasRunnableNodeTestScript(tc.script); got != tc.want {
				t.Fatalf("hasRunnableNodeTestScript(%q) = %t, want %t", tc.script, got, tc.want)
			}
		})
	}
}
