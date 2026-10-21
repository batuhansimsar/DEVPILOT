package doctor

// hasPythonProjectMarker recognizes supported Python project metadata without
// reading any configuration or executing project-controlled commands.
// Pipenv projects may contain only Pipfile or a committed Pipfile.lock.
// Legacy setuptools projects may use setup.py or setup.cfg without pyproject.toml.
func hasPythonProjectMarker(root string) bool {
	for _, name := range []string{"requirements.txt", "pyproject.toml", "pytest.ini", "Pipfile", "Pipfile.lock", "setup.py", "setup.cfg", "tox.ini", "uv.lock", "poetry.lock", "pdm.lock", "environment.yml", "environment.yaml"} {
		if hasMarker(root, name) {
			return true
		}
	}
	return false
}
