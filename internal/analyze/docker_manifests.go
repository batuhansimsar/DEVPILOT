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
	// Compose accepts service-specific filenames such as api.compose.yaml.
	// The leading component must be nonempty (not .compose.yaml).
	for _, suffix := range []string{".compose.yml", ".compose.yaml"} {
		if strings.HasSuffix(lower, suffix) && len(lower) > len(suffix) {
			return "Docker Compose", true
		}
	}
	for _, prefix := range []string{"compose", "docker-compose"} {
		if lower == prefix+".yml" || lower == prefix+".yaml" {
			return "Docker Compose", true
		}
		if !strings.HasPrefix(lower, prefix+".") {
			continue
		}
		for _, extension := range []string{".yml", ".yaml"} {
			if !strings.HasSuffix(lower, extension) {
				continue
			}
			qualifier := strings.TrimSuffix(strings.TrimPrefix(lower, prefix+"."), extension)
			// Empty or dot-terminated qualifiers are not meaningful Compose
			// variants (e.g. compose..yml or compose.prod..yaml).
			if qualifier != "" && !strings.HasSuffix(qualifier, ".") {
				return "Docker Compose", true
			}
		}
	}
	return "", false
}
