package analyze

import "testing"

func TestQualifiedComposeContainerConfigs(t *testing.T) {
	cases := map[string]bool{
		"compose.override.yml":        true,
		"compose.dev.yaml":           true,
		"docker-compose.override.yml": true,
		"docker-compose.prod.eu.yaml": true,
		"compose.yml":                true,
		"docker-compose.yaml":         true,
		"api.compose.yml":            true,
		"compose..yml":               false,
		"compose.prod..yaml":         false,
		"compose.override.yml.bak":    false,
		"Dockerfile.dev.BAK":          false,
		"Dockerfile.dev.DOCKERIGNORE": false,
		"Containerfile.prod.TMP":      false,
		"compose.override.yml.BACKUP": false,
		"docker-compose.dev.yaml.tmp": false,
		"docker-compose.dev.json":     false,
		"not-compose.dev.yml":        false,
	}
	for name, expected := range cases {
		if got := isContainerConfig(name); got != expected {
			t.Errorf("isContainerConfig(%q) = %v; want %v", name, got, expected)
		}
	}
}
