package analyze

import "testing"

func TestIsCIConfig(t *testing.T) {
	cases := []struct {
		path string
		want bool
	}{
		{".github/workflows/build.yml", true},
		{".github/workflows/build.yaml", true},
		{".gitlab-ci.yml", true},
		{"azure-pipelines.yml", true},
		{"Jenkinsfile", true},
		{".circleci/config.yml", true},
		{".circleci/config.yaml", true},
		{"bitbucket-pipelines.yml", true},
		{".travis.yml", true},
		{".drone.yml", true},
		{".buildkite/pipeline.yml", true},
		{".buildkite/pipeline.yaml", true},
		{".circleci/README.md", false},
		{"nested/.circleci/config.yml", false},
		{".github/README.yml", false},
		{"src/Jenkinsfile", false},
		{"bitbucket-pipelines.yml.bak", false},
		{".github/workflows/notes.txt", false},
	}
	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Fatalf("isCIConfig(%q) = %v, want %v", tc.path, got, tc.want)
			}
		})
	}
}
