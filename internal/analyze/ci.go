package analyze

import "strings"

// isCIConfig matches repository CI entrypoints by path, without opening or
// interpreting potentially untrusted pipeline definitions. Paths are slash-
// separated relative to the repository root.
func isCIConfig(path string) bool {
	const workflows = ".github/workflows/"
	if strings.HasPrefix(path, workflows) {
		// GitHub only discovers workflow files directly in this directory.
		// Nested YAML files (for example, archived workflows) are not run.
		filename := strings.TrimPrefix(path, workflows)
		return filename != "" && !strings.Contains(filename, "/") &&
			(strings.HasSuffix(filename, ".yml") || strings.HasSuffix(filename, ".yaml"))
	}
	switch path {
	case ".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile",
		".circleci/config.yml", ".circleci/config.yaml",
		"bitbucket-pipelines.yml", ".travis.yml", ".drone.yml",
		".buildkite/pipeline.yml", ".buildkite/pipeline.yaml":
		return true
	default:
		return false
	}
}
