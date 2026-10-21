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
		if line == section {
			return true
		}
	}
	return false
}
