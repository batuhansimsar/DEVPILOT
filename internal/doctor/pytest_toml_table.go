package doctor

import "strings"

// hasPytestTOMLTable finds explicit pytest configuration table headers without
// mistaking text inside TOML multiline strings for real tables. The caller
// bounds the size of pyproject.toml and reads only a trusted regular file.
func hasPytestTOMLTable(data []byte) bool {
	content := strings.TrimPrefix(string(data), "\ufeff")
	var multiline byte // The quote delimiter of an open TOML multiline string.
	for _, line := range strings.Split(content, "\n") {
		if multiline == 0 {
			trimmed := strings.TrimSpace(line)
			for _, header := range []string{"[tool.pytest.ini_options]", "[tool.pytest]"} {
				if strings.HasPrefix(trimmed, header) {
					rest := strings.TrimSpace(strings.TrimPrefix(trimmed, header))
					if rest == "" || strings.HasPrefix(rest, "#") {
						return true
					}
				}
			}
		}

		// Track multiline basic (""") and literal (''') strings. Single-line
		// strings and comments cannot start a multiline value, even if they
		// contain quote delimiters in their text.
		var quoted byte
		for i := 0; i < len(line); {
			ch := line[i]
			if multiline != 0 {
				if ch == '\\' && multiline == '"' {
					i += 2 // Escape consumes the next byte, including a quote.
					continue
				}
				if i+2 < len(line) && ch == multiline && line[i+1] == ch && line[i+2] == ch {
					multiline = 0
					i += 3
					continue
				}
				i++
				continue
			}
			if quoted != 0 {
				if ch == '\\' && quoted == '"' {
					i += 2
					continue
				}
				if ch == quoted {
					quoted = 0
				}
				i++
				continue
			}
			if ch == '#' {
				break
			}
			if ch == '"' || ch == '\'' {
				if i+2 < len(line) && line[i+1] == ch && line[i+2] == ch {
					multiline = ch
					i += 3
				} else {
					quoted = ch
					i++
				}
				continue
			}
			i++
		}
	}
	return false
}
