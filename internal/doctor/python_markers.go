package doctor

import "strings"

// hasPythonProjectMarker recognizes supported Python project metadata without
// executing project-controlled commands. A pyproject.toml identifies a Python
// project, but is not itself evidence of a pytest configuration.
// Only regular files inside the project are trusted.
func hasPytestConfig(root string) bool {
	for _, name := range []string{"pytest.toml", ".pytest.toml", "pytest.ini", ".pytest.ini"} {
		if hasMarker(root, name) {
			return true
		}
	}

	// pyproject.toml is general Python metadata, unlike the dedicated
	// pytest configuration files. Inspect it via the bounded, symlink-safe
	// reader, and only recognize explicit pytest table headers.
	data, found, err := readMarker(root, "pyproject.toml")
	if err != nil || !found {
		return false
	}
	for _, raw := range strings.Split(strings.TrimPrefix(string(data), "\ufeff"), "\n") {
		line := strings.TrimSpace(raw)
		line, _, _ = strings.Cut(line, "#")
		line = strings.TrimSpace(line)
		if line == "[tool.pytest.ini_options]" || line == "[tool.pytest]" {
			return true
		}
	}
	return false
}

func hasPythonProjectMarker(root string) bool {
	if hasPytestConfig(root) {
		return true
	}
	for _, name := range []string{"pyproject.toml", "requirements.txt", "Pipfile", "Pipfile.lock", "setup.py", "setup.cfg", "tox.ini", "uv.lock", "poetry.lock", "pdm.lock", "environment.yml", "environment.yaml"} {
		if hasMarker(root, name) {
			return true
		}
	}
	return false
}
