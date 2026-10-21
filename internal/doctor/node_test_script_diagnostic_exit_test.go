package doctor

import "testing"

func TestDiagnosticOnlyScriptDoesNotCountAsTest(t *testing.T) {
	for _, tt := range []struct {
		name, script string
		want         bool
	}{
		{"semicolon nonzero exit remains conservative", "echo \"Not implemented\"; exit 1", true},
		{"semicolon success exit", "printf 'Skipping tests'; exit 0", false},
		{"multiple output commands", "echo initializing && printf \"Not ready\"; exit 0;", false},
		{"and success exit", "echo \"no tests here\" && exit 0", false},
		{"and nonzero exit remains conservative", "echo \"no tests here\" && exit 127", true},
		{"literal operators in message", "echo 'test && test; skip'; exit 0", false},
		{"actual tests after output", "echo starting; node --test", true},
		{"actual tests after diagnostic", "echo waiting; exit 1 || node --test", true},
		{"actually invokes test before exit", "npm run check && exit 0", true},
		{"non-output fallback", "echo setup && node --test && exit 0", true},
		{"shell expansion", "echo \"$(node --test)\"; exit 0", true},
		{"background command", "echo hi & node --test; exit 0", true},
		{"string contains false exit", "echo 'testing; exit 0' && node --test", true},
		{"standalone exit 1", "exit 1", false},
		{"npm init", "echo \"Error: no test specified\" && exit 1", false},
	} {
		t.Run(tt.name, func(t *testing.T) {
			if got := hasRunnableNodeTestScript(tt.script); got != tt.want {
				t.Fatalf("script %q runnable=%v want %v", tt.script, got, tt.want)
			}
		})
	}
}
