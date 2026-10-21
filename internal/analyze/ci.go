package analyze

import "strings"

// isCIConfig matches repository CI entrypoints by path, without opening or
// interpreting potentially untrusted pipeline definitions. Paths are slash-
// separated relative to the repository root.
func isCIConfig(path string) bool {
	// GitHub, Gitea, Forgejo, and Woodpecker discover workflows directly
	// in their respective directories, never nested YAML files.
	for _, workflows := range []string{".github/workflows/", ".gitea/workflows/", ".forgejo/workflows/", ".woodpecker/"} {
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
		".buildkite/pipeline.yml", ".buildkite/pipeline.yaml",
		".woodpecker.yml", ".woodpecker.yaml", "bitrise.yml",
		"appveyor.yml", ".appveyor.yml",
		".semaphore/semaphore.yml",           // Semaphore 2.0 default pipeline.
		"cloudbuild.yaml", "cloudbuild.json", // Google Cloud Build configs.
		"buildspec.yml", "buildspec.yaml", // AWS CodeBuild
		"amplify.yml", // AWS Amplify Hosting build specification.
		"cloudbuild.yml", "appveyor.yaml", ".appveyor.yaml",
		".semaphore/semaphore.yaml",
		".teamcity/settings.kts", // TeamCity Kotlin DSL versioned settings.
		"codefresh.yml",          // Codefresh default root pipeline definition.
		"wercker.yml":            // Wercker's default pipeline definition.
		return true
	case ".cirrus.yml":
		return true
	default:
		return false
	}
}
