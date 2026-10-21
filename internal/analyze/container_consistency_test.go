package analyze

import "testing"

func TestContainerManifestDiscoveryConsistency(t *testing.T) {
	cases := []struct {
		name string
		kind string
	}{
		{"DOCKERFILE", "Docker"},
		{"DockerFile.PROD", "Docker"},
		{"Api.DOCKERFILE", "Docker"},
		{"CONTAINERFILE", "Containerfile"},
		{"api.CONTAINERFILE", "Containerfile"},
		{"COMPOSE.YAML", "Docker Compose"},
		{"Docker-Compose.PROD.YML", "Docker Compose"},
		{"api.compose.yaml", "Docker Compose"},
		{"API.COMPOSE.YML", "Docker Compose"},
		{"web.api.compose.yml", "Docker Compose"},
		{"Dockerfile.", ""},
		{".compose.yaml", ""},
		{"compose..yml", ""},
		{"compose.prod..yaml", ""},
		{"api.compose..yaml", ""},
		{"api.compose.yml.bak", ""},
		{"DOCKERFILE.DOCKERIGNORE", ""},
		{"api.DOCKERFILE.SWP", ""},
		{"not-compose.yml", ""},
		{"plain.txt", ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			kind, manifest := dockerManifestKind(tc.name)
			container := isContainerConfig(tc.name)
			if kind != tc.kind || manifest != (tc.kind != "") || container != manifest {
				t.Errorf("%q: kind=%q manifest=%v container=%v, want kind=%q", tc.name, kind, manifest, container, tc.kind)
			}
		})
	}
}
