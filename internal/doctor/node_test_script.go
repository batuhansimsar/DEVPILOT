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

// shellOnlyOutput reports scripts that only print text, including sequences of
// output-only commands separated by semicolons. Shell operators inside quoted
// literal output are harmless; operators outside quotes and expansion within
// double quotes could execute tests and must remain classified as runnable.
func shellOnlyOutput(script string) bool {
	script = strings.TrimSpace(script)
	isOutputCommand := func(command string) bool {
		fields := strings.Fields(strings.TrimSpace(command))
		return len(fields) > 0 && (fields[0] == "echo" || fields[0] == "printf")
	}
	var quote byte
	start := 0
	sawOutput := false
	for i := 0; i < len(script); i++ {
		ch := script[i]
		if ch == '\r' || ch == '\n' {
			return false
		}
		switch quote {
		case '\'':
			if ch == '\'' {
				quote = 0
			}
		case '"':
			// Shell substitutions and escapes are not literal output.
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
			case ';':
				if !isOutputCommand(script[start:i]) {
					return false
				}
				sawOutput = true
				start = i + 1
			case '&', '|', '$', '<', '>', '\\':
				return false
			case 96:
				return false
			}
		}
	}
	if quote != 0 {
		return false
	}
	last := strings.TrimSpace(script[start:])
	return (last == "" && sawOutput) || isOutputCommand(last)
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
