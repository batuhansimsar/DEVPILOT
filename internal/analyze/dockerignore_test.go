package analyze

import "testing"

func TestDockerignoreIsNotAContainerManifest(t *testing.T) {
	for _, filename := range []string{
		"Dockerfile.dockerignore",
		"Dockerfile.prod.dockerignore",
		"Containerfile.dockerignore",
		"Containerfile.dev.dockerignore",
		"DOCKERFILE.DOCKERIGNORE",
	} {
		t.Run(filename, func(t *testing.T) {
			if kind, ok := dockerManifestKind(filename); ok || kind != "" {
				t.Errorf("dockerManifestKind(%q) = (%q, %v); want no manifest", filename, kind, ok)
			}
			if filename != "DOCKERFILE.DOCKERIGNORE" && isContainerConfig(filename) {
				t.Errorf("isContainerConfig(%q) = true; Docker ignore files are not manifests", filename)
			}
		})
	}
}

func TestDockerRecipeStillRecognizedWithMatchingIgnoreFile(t *testing.T) {
	for _, filename := range []string{"Dockerfile", "Dockerfile.prod"} {
		if kind, ok := dockerManifestKind(filename); !ok || kind != "Docker" {
			t.Errorf("dockerManifestKind(%q) = (%q, %v); want Docker", filename, kind, ok)
		}
		if !isContainerConfig(filename) {
			t.Errorf("isContainerConfig(%q) = false; want true", filename)
		}
	}
	for _, filename := range []string{"Containerfile", "Containerfile.dev"} {
		if kind, ok := dockerManifestKind(filename); !ok || kind != "Containerfile" {
			t.Errorf("dockerManifestKind(%q) = (%q, %v); want Containerfile", filename, kind, ok)
		}
		if !isContainerConfig(filename) {
			t.Errorf("isContainerConfig(%q) = false; want true", filename)
		}
	}
}
