package analyze

import "testing"

func TestDockerRecipeDiscoverySkipsMoreEditorBackups(t *testing.T) {
	cases := []struct{ name, kind string }{
		{"Dockerfile.orig", ""},
		{"Dockerfile.prod.save", ""},
		{"Containerfile.rej", ""},
		{"Dockerfile.swo", ""},
		{"Dockerfile.swa", ""},
		{"api.Containerfile.svz", ""},
		{"Dockerfile.saa", ""},
		{"Dockerfile.~12~", ""},
		{"Dockerfile.dev", "Docker"},
		{"Dockerfile.swq", "Docker"},
		{"api.Containerfile", "Containerfile"},
		{"compose.override.yaml", "Docker Compose"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			kind, ok := dockerManifestKind(tc.name)
			if kind != tc.kind || ok != (tc.kind != "") {
				t.Fatalf("dockerManifestKind(%q) = (%q, %v), want %q", tc.name, kind, ok, tc.kind)
			}
			if isContainerConfig(tc.name) != (tc.kind != "") {
				t.Fatalf("container detection disagrees for %q", tc.name)
			}
		})
	}
}
