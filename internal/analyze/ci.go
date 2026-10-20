package analyze

import "strings"

// isCIConfig matches repository CI entrypoints by path, without opening or
// interpreting potentially untrusted pipeline definitions. Paths are slash-
// separated relative to the repository root.
func isCIConfig(path string) bool {
	if strings.HasPrefix(path, ".github/workflows/") {
		return strings.HasSuffix(path, ".yml") || strings.HasSuffix(path, ".yaml")
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
