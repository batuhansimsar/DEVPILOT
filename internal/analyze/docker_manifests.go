package analyze

import "strings"

// dockerManifestKind recognizes Docker and Docker Compose configurations by
// filename only. It never invokes Docker or project-controlled scripts.
func dockerManifestKind(name string) (string, bool) {
	lower := strings.ToLower(name)
	if lower == "dockerfile" || strings.HasPrefix(lower, "dockerfile.") {
		return "Docker", true
	}
	for _, prefix := range []string{"compose", "docker-compose"} {
		if lower == prefix+".yml" || lower == prefix+".yaml" ||
			(strings.HasPrefix(lower, prefix+".") &&
				(strings.HasSuffix(lower, ".yml") || strings.HasSuffix(lower, ".yaml"))) {
			return "Docker Compose", true
		}
	}
	return "", false
}
