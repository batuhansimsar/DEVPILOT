package analyze

import "testing"

func TestDockerRecipeQualifierSegments(t *testing.T) {
	cases := []struct {
		name string
		kind string
	}{
		{"Dockerfile", "Docker"},
		{"compose.prod.eu.yaml", "Docker Compose"},
		{"api.prod.compose.yml", "Docker Compose"},
		{"Dockerfile.dev", "Docker"},
		{"Dockerfile.prod.api", "Docker"},
		{"api.Dockerfile", "Docker"},
		{"api.prod.Dockerfile", "Docker"},
		{"CONTAINERFILE.PROD.API", "Containerfile"},
		{"api.Containerfile", "Containerfile"},
		{"Dockerfile.", ""},
		{"api..compose.yaml", ""},
		{"api..prod.compose.yml", ""},
		{"compose.prod..eu.yaml", ""},
		{"Dockerfile..dev", ""},
		{"Dockerfile.prod..api", ""},
		{"Dockerfile.dev.", ""},
		{"api..Dockerfile", ""},
		{"api..prod.Containerfile", ""},
		{"Containerfile..prod", ""},
		{"Containerfile.prod..api", ""},
		{"api..Containerfile", ""},
		{".Dockerfile", ""},
		{"Containerfile.", ""},
		{"Dockerfile.prod.bak", ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, ok := dockerManifestKind(tc.name)
			if got != tc.kind || ok != (tc.kind != "") {
				t.Errorf("dockerManifestKind(%q) = (%q, %v); want %q", tc.name, got, ok, tc.kind)
			}
			if isContainerConfig(tc.name) != (tc.kind != "") {
				t.Errorf("isContainerConfig(%q) disagrees with manifest kind", tc.name)
			}
		})
	}
}
