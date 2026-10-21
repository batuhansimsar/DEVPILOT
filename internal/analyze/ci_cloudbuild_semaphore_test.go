package analyze

import "testing"

// Confirm that only the standard entrypoints are automatically discovered.
// Explicitly configured custom paths cannot be inferred from file names.
func TestIsCIConfigCloudBuildAndSemaphore(t *testing.T) {
	cases := []struct {
		path string
		want bool
	}{
		{".semaphore/semaphore.yml", true},
		{"cloudbuild.yaml", true},
		{"cloudbuild.json", true},
		{".semaphore/semaphore.yml.old", false},
		{"nested/.semaphore/semaphore.yml", false},
		{".semaphore/README.md", false},
		{".semaphore/nested/semaphore.yml", false},
		{"cloudbuild.yaml.bak", false},
		{"nested/cloudbuild.yaml", false},
		{"cloudbuild.json.tmp", false},
	}
	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Errorf("isCIConfig(%q) = %v; want %v", tc.path, got, tc.want)
			}
		})
	}
}
