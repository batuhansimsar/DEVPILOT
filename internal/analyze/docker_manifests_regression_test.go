package analyze

import "testing"

func TestDockerManifestKindContainerfileAndBackupHandling(t *testing.T) {
	cases := []struct {
		name string
		kind string
	}{
		{"Containerfile", "Containerfile"},
		{"Containerfile.prod", "Containerfile"},
		{"api.Containerfile", "Containerfile"},
		{"Dockerfile", "Docker"},
		{"Dockerfile.dev", "Docker"},
		{"api.Dockerfile", "Docker"},
		{"compose.dev.yml", "Docker Compose"},
		{"docker-compose.override.yaml", "Docker Compose"},
		{"Dockerfile.", ""},
		{"Containerfile.", ""},
		{"Dockerfile.bak", ""},
		{"Dockerfile.dev.backup", ""},
		{"api.Containerfile.tmp", ""},
		{"Dockerfile.prod.swp", ""},
		{"Containerfile~", ""},
		{"compose.override.yml.bak", ""},
		{"not-compose.yaml", ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			kind, ok := dockerManifestKind(tc.name)
			if kind != tc.kind || ok != (tc.kind != "") {
				t.Fatalf("dockerManifestKind(%q) = (%q, %v); want kind %q", tc.name, kind, ok, tc.kind)
			}
		})
	}
}
