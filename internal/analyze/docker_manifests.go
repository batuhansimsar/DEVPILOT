package analyze

import "strings"

// dockerManifestKind recognizes Docker, Containerfile, and Compose manifests by
// filename only. Temporary, backup, and Docker ignore files must not appear as manifests.
func dockerManifestKind(name string) (string, bool) {
	lower := strings.ToLower(name)
	for _, suffix := range []string{".bak", ".backup", ".tmp", ".orig", ".save", ".rej", ".swp", "~", ".dockerignore"} {
		if strings.HasSuffix(lower, suffix) {
			return "", false
		}
	}
	// Vim rotates .swp through .swa, then .svz down to .saa. These are
	// editor swap files, not deployable Docker recipes.
	if len(lower) >= 4 {
		suffix := lower[len(lower)-4:]
		if suffix[:2] == ".s" && ((suffix[2] == 'w' && suffix[3] >= 'a' && suffix[3] <= 'p') ||
			(suffix[2] >= 'a' && suffix[2] <= 'v' && suffix[3] >= 'a' && suffix[3] <= 'z')) {
			return "", false
		}
	}
	// A qualified recipe/Compose name must have nonempty dot-delimited
	// components. Do not mistake malformed names for deployable manifests.
	validQualifier := func(value string) bool {
		return value != "" && !strings.HasPrefix(value, ".") &&
			!strings.HasSuffix(value, ".") && !strings.Contains(value, "..")
	}
	isRecipe := func(base string) bool {
		if lower == base {
			return true
		}
		if strings.HasPrefix(lower, base+".") &&
			validQualifier(strings.TrimPrefix(lower, base+".")) {
			return true
		}
		return strings.HasSuffix(lower, "."+base) &&
			validQualifier(strings.TrimSuffix(lower, "."+base))
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
		if strings.HasSuffix(lower, suffix) &&
			validQualifier(strings.TrimSuffix(lower, suffix)) {
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
			// Reject empty or repeated qualifier segments for Compose variants.
			if validQualifier(qualifier) {
				return "Docker Compose", true
			}
		}
	}
	return "", false
}
