package doctor

import "strings"

// hasRunnableNodeTestScript avoids recommending an empty or npm-init default
// placeholder as a real test suite. It never evaluates or executes the script.
func hasRunnableNodeTestScript(script string) bool {
	trimmed := strings.TrimSpace(script)
	if trimmed == "" {
		return false
	}
	lower := strings.ToLower(trimmed)
	// `npm init` commonly creates this failing placeholder. Requiring both
	// its message and an echo-prefix avoids rejecting real test commands.
	if strings.HasPrefix(lower, "echo ") &&
		strings.Contains(lower, "no test specified") &&
		strings.Contains(lower, "exit 1") {
		return false
	}
	return true
}
