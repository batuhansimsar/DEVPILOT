package analyze

import "strings"

// dockerManifestKind recognizes Docker, Containerfile, and Compose manifests by
// filename only. Temporary, backup, and Docker ignore files must not appear as manifests.
func dockerManifestKind(name string) (string, bool) {
	lower := strings.ToLower(name)
	for _, suffix := range []string{".bak", ".backup", ".tmp", ".swp", "~", ".dockerignore"} {
		if strings.HasSuffix(lower, suffix) {
			return "", false
		}
	}
	isRecipe := func(base string) bool {
		return lower == base ||
			(strings.HasPrefix(lower, base+".") && len(lower) > len(base)+1) ||
			(strings.HasSuffix(lower, "."+base) && len(lower) > len(base)+1)
	}
	if isRecipe("dockerfile") {
		return "Docker", true
	}
	if isRecipe("containerfile") {
		return "Containerfile", true
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
