package doctor

import "strings"

// hasPytestINISection accepts only a top-level INI section header. Indented
// lines can continue an earlier option value, and must not select a test runner.
func hasPytestINISection(data []byte, section string) bool {
	for index, raw := range strings.Split(string(data), "\n") {
		if index == 0 {
			raw = strings.TrimPrefix(raw, "\ufeff")
		}
		line := strings.TrimRight(raw, "\r\t ")
		if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(line, ";") {
			continue
		}
		// INI parsers used by pytest allow a trailing '#' or ';' comment
		// after the closing bracket, with or without intervening spaces.
		// Keep matching anchored at column zero and reject unrelated suffixes.
		if strings.HasPrefix(line, section) {
			tail := strings.TrimSpace(line[len(section):])
			if tail == "" || strings.HasPrefix(tail, "#") || strings.HasPrefix(tail, ";") {
				return true
			}
		}
	}
	return false
}
