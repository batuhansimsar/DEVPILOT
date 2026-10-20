package analyze

import "strings"

// isContainerConfig recognizes common Docker, Compose, and Podman manifests by
// filename only. No manifest contents are opened, parsed, or executed.
func isContainerConfig(name string) bool {
	for _, suffix := range []string{".bak", ".backup", ".tmp", ".swp", "~", ".dockerignore"} {
		if strings.HasSuffix(name, suffix) {
			return false
		}
	}
	switch name {
	case "Dockerfile", "Containerfile", "compose.yml", "compose.yaml",
		"docker-compose.yml", "docker-compose.yaml":
		return true
	}
	for _, prefix := range []string{"Dockerfile.", "Containerfile."} {
		if strings.HasPrefix(name, prefix) && len(name) > len(prefix) {
			return true
		}
	}
	for _, suffix := range []string{".Dockerfile", ".Containerfile", ".compose.yml", ".compose.yaml"} {
		if strings.HasSuffix(name, suffix) && len(name) > len(suffix) {
			return true
		}
	}
	// Compose supports qualified names such as compose.override.yml and
	// docker-compose.prod.yaml. Reject an empty qualifier (compose..yml).
	for _, prefix := range []string{"compose.", "docker-compose."} {
		if !strings.HasPrefix(name, prefix) {
			continue
		}
		qualifier := strings.TrimPrefix(name, prefix)
		for _, extension := range []string{".yml", ".yaml"} {
			if strings.HasSuffix(qualifier, extension) &&
				len(qualifier) > len(extension) &&
				qualifier[len(qualifier)-len(extension)-1] != '.' {
				return true
			}
		}
	}
	return false
}
