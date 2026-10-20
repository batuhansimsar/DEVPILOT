package doctor

import (
	"bufio"
	"bytes"
	"regexp"
	"strings"
)

// pythonHasPytest reports a test runner only when supported project files
// contain evidence of pytest. A generic pyproject.toml is not evidence.
// All inspected files are read through the bounded, symlink-refusing reader.
func pythonHasPytest(root string) bool {
	if hasMarker(root, "pytest.ini") || hasMarker(root, "conftest.py") {
		return true
	}
	if data, found, err := readMarker(root, "requirements.txt"); err == nil && found {
		for _, line := range bytes.Split(data, []byte("\n")) {
			s := strings.TrimSpace(string(line))
			if strings.HasPrefix(s, "#") {
				continue
			}
			if pythonRequirement.MatchString(s) {
				return true
			}
		}
	}
	if data, found, err := readMarker(root, "pyproject.toml"); err == nil && found {
		section := ""
		scanner := bufio.NewScanner(bytes.NewReader(data))
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if line == "" || strings.HasPrefix(line, "#") {
				continue
			}
			if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
				section = strings.Trim(line, "[]")
				if section == "tool.pytest.ini_options" {
					return true
				}
				continue
			}
			if (section == "tool.poetry.dev-dependencies" ||
				(strings.HasPrefix(section, "tool.poetry.group.") && strings.HasSuffix(section, ".dependencies"))) &&
				pythonPoetryRequirement.MatchString(line) {
				return true
			}
			if (section == "project" || section == "project.optional-dependencies" || section == "dependency-groups") &&
				pythonQuotedRequirement.MatchString(strings.SplitN(line, "#", 2)[0]) {
				return true
			}
		}
	}
	if data, found, err := readMarker(root, "setup.cfg"); err == nil && found {
		for _, line := range bytes.Split(data, []byte("\n")) {
			if strings.EqualFold(strings.TrimSpace(string(line)), "[tool:pytest]") {
				return true
			}
		}
	}
	return false
}

var pythonRequirement = regexp.MustCompile(`(?i)^pytest(?:\[[^]]+\])?(?:\s*(?:[!<>=~;]|$))`)
var pythonPoetryRequirement = regexp.MustCompile(`^pytest\s*=`)
var pythonQuotedRequirement = regexp.MustCompile(`["']pytest(?:\[[^]]+\])?(?:[!<>=~;]|["'])`)
