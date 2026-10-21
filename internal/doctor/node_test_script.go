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

// shellOnlyOutput reports scripts that solely print text. Rejecting shell
// metacharacters avoids hiding actual tests in pipelines, command substitutions,
// multiline scripts, redirections, or chained commands. An ordinary semicolon
// at the end of a single command is harmless.
func shellOnlyOutput(script string) bool {
	script = strings.TrimSpace(strings.TrimSuffix(strings.TrimSpace(script), ";"))
	if strings.ContainsAny(script, ";&|$`<>\\\r\n") {
		return false
	}
	fields := strings.Fields(script)
	return len(fields) > 0 && (fields[0] == "echo" || fields[0] == "printf")
}

// hasRunnableNodeTestScript avoids recommending empty, no-op, or npm-init
// placeholder scripts as real test suites. It never evaluates or executes them.
func hasRunnableNodeTestScript(script string) bool {
	trimmed := strings.TrimSpace(script)
	if trimmed == "" || npmInitPlaceholder.MatchString(trimmed) || shellOnlyOutput(trimmed) {
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
