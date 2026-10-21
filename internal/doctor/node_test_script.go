package doctor

import (
	"regexp"
	"strconv"
	"strings"
)

// npmInitPlaceholder matches the generated failing `npm init` test script,
// not arbitrary scripts which happen to contain the same message. Anchoring
// prevents discarding real tests chained after the default message.
var npmInitPlaceholder = regexp.MustCompile(`(?i)^echo[ \t]+(?:"(?:error:[ \t]*)?no test specified"|'(?:error:[ \t]*)?no test specified'|(?:error:[ \t]*)?no test specified)[ \t]*&&[ \t]*exit[ \t]+1[ \t]*;?$`)

// hasRunnableNodeTestScript avoids recommending empty, no-op, or npm-init
// placeholder scripts as real test suites. It never evaluates or executes them.
func hasRunnableNodeTestScript(script string) bool {
	trimmed := strings.TrimSpace(script)
	if trimmed == "" || npmInitPlaceholder.MatchString(trimmed) {
		return false
	}
	// Standalone shell built-ins and exits do not run tests. Require a full
	// match so compound commands such as "true && node --test" stay runnable.
	simple := strings.TrimSpace(strings.TrimSuffix(trimmed, ";"))
	switch simple {
	case ":", "true", "false", "exit":
		return false
	}
	if fields := strings.Fields(simple); len(fields) == 2 && fields[0] == "exit" {
		if _, err := strconv.Atoi(fields[1]); err == nil {
			return false
		}
	}
	return true
}
