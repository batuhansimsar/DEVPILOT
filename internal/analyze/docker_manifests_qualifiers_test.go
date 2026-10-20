package analyze

import "testing"

// Manifest discovery and container-config discovery must agree about invalid
// Compose qualifiers, so a malformed filename cannot appear as a manifest.
func TestDockerManifestKindRejectsMalformedComposeQualifiers(t *testing.T) {
	for _, name := range []string{
		"compose..yml",
		"compose..yaml",
		"compose.prod..yaml",
		"compose.prod..YML",
		"docker-compose..yml",
		"docker-compose.dev..yaml",
		"docker-compose..YAML",
	} {
		t.Run(name, func(t *testing.T) {
			if kind, ok := dockerManifestKind(name); ok || kind != "" {
				t.Fatalf("dockerManifestKind(%q) = (%q, %v), want no manifest", name, kind, ok)
			}
		})
	}
}

func TestDockerManifestKindAcceptsQualifiedCompose(t *testing.T) {
	for _, name := range []string{
		"compose.yml",
		"compose.dev.yml",
		"compose.prod.eu.yaml",
		"docker-compose.yaml",
		"docker-compose.test.yml",
		"DOCKER-COMPOSE.PROD.YAML",
	} {
		t.Run(name, func(t *testing.T) {
			if kind, ok := dockerManifestKind(name); !ok || kind != "Docker Compose" {
				t.Fatalf("dockerManifestKind(%q) = (%q, %v), want Docker Compose", name, kind, ok)
			}
		})
	}
}
