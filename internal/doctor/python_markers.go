package doctor

// hasPythonProjectMarker recognizes supported Python project metadata without
// reading any configuration or executing project-controlled commands.
// Pipenv projects may contain only Pipfile or a committed Pipfile.lock.
// Legacy setuptools projects may use setup.py or setup.cfg without pyproject.toml.
// hasPytestConfig detects legacy INI files and native TOML config files
// introduced in pytest 9. Only regular files inside the project are trusted.
func hasPytestConfig(root string) bool {
	for _, name := range []string{"pytest.toml", ".pytest.toml", "pytest.ini", ".pytest.ini", "pyproject.toml"} {
		if hasMarker(root, name) {
			return true
		}
	}
	return false
}

func hasPythonProjectMarker(root string) bool {
	if hasPytestConfig(root) {
		return true
	}
	for _, name := range []string{"requirements.txt", "Pipfile", "Pipfile.lock", "setup.py", "setup.cfg", "tox.ini", "uv.lock", "poetry.lock", "pdm.lock", "environment.yml", "environment.yaml"} {
		if hasMarker(root, name) {
			return true
		}
	}
	return false
}
