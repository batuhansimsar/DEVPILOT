package analyze

import "testing"

func TestCIConfigRecognizesGiteaAndForgejoWorkflows(t *testing.T) {
	for _, prefix := range []string{".gitea/workflows/", ".forgejo/workflows/"} {
		for _, name := range []string{"build.yml", "release.yaml"} {
			if !isCIConfig(prefix + name) {
				t.Errorf("did not recognize workflow %s%s", prefix, name)
			}
		}
		for _, name := range []string{"", "nested/build.yml", "archived.txt", "build.yml.bak"} {
			if isCIConfig(prefix + name) {
				t.Errorf("incorrectly recognized workflow %s%s", prefix, name)
			}
		}
	}
}
