package analyze

import "strings"

// isContainerConfig recognizes common Docker, Compose, and Podman manifests by
// filename only. No manifest contents are opened, parsed, or executed.
func isContainerConfig(name string) bool {
	for _, suffix := range []string{".bak", ".backup", ".tmp", ".swp", "~"} {
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
	return false
}
