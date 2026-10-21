package doctor

import (
	"regexp"
	"strings"
)

// npmInitPlaceholder matches the generated failing `npm init` test script,
// not arbitrary scripts which happen to contain the same message. Anchoring
// prevents discarding real tests chained after the default message.
var npmInitPlaceholder = regexp.MustCompile(`(?i)^echo[ \t]+(?:"(?:error:[ \t]*)?no test specified"|'(?:error:[ \t]*)?no test specified'|(?:error:[ \t]*)?no test specified)[ \t]*&&[ \t]*exit[ \t]+1[ \t]*;?$`)

// hasRunnableNodeTestScript avoids recommending an empty or npm-init default
// placeholder as a real test suite. It never evaluates or executes the script.
func hasRunnableNodeTestScript(script string) bool {
	trimmed := strings.TrimSpace(script)
	return trimmed != "" && !npmInitPlaceholder.MatchString(trimmed)
}
