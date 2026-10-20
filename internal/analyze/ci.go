package analyze

import "strings"

// isCIConfig matches repository CI entrypoints by path, without opening or
// interpreting potentially untrusted pipeline definitions. Paths are slash-
// separated relative to the repository root.
func isCIConfig(path string) bool {
	// GitHub, Gitea, and Forgejo only discover workflow files directly
	// in their respective workflow directories, never nested YAML files.
	for _, workflows := range []string{".github/workflows/", ".gitea/workflows/", ".forgejo/workflows/"} {
		if strings.HasPrefix(path, workflows) {
			filename := strings.TrimPrefix(path, workflows)
			return filename != "" && !strings.Contains(filename, "/") &&
				(strings.HasSuffix(filename, ".yml") || strings.HasSuffix(filename, ".yaml"))
		}
	}
	switch path {
	case ".gitlab-ci.yml", "azure-pipelines.yml", "azure-pipelines.yaml", "Jenkinsfile",
		".circleci/config.yml", ".circleci/config.yaml",
		"bitbucket-pipelines.yml", ".travis.yml", ".drone.yml", ".drone.yaml",
		".buildkite/pipeline.yml", ".buildkite/pipeline.yaml":
		return true
	default:
		return false
	}
}
