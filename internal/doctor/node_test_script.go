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

// shellOnlyOutput reports scripts that solely print text. Shell operators in
// quoted literal output are harmless, but operators outside quotes (and shell
// substitutions inside double quotes) may run real commands. Be conservative:
// an ambiguous script stays runnable rather than hiding a test suite.
func shellOnlyOutput(script string) bool {
	script = strings.TrimSpace(strings.TrimSuffix(strings.TrimSpace(script), ";"))
	var quote byte
	for i := 0; i < len(script); i++ {
		ch := script[i]
		if ch == '\r' || ch == '\n' {
			return false
		}
		switch quote {
		case '\'':
			// No shell expansion occurs within single quotes.
			if ch == '\'' {
				quote = 0
			}
		case '"':
			// Expansion/escaping within double quotes can execute commands.
			if ch == '$' || ch == 96 || ch == '\\' {
				return false
			}
			if ch == '"' {
				quote = 0
			}
		default:
			switch ch {
			case '\'', '"':
				quote = ch
			case ';', '&', '|', '$', '<', '>', '\\':
				return false
			case 96:
				return false
			}
		}
	}
	if quote != 0 {
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
