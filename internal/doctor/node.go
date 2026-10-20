package doctor

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
)

// A packageManager declaration must identify a fixed Corepack release rather
// than a tag, range, URL, or arbitrary command argument. Permit prerelease,
// build metadata, and Corepack's optional integrity hash suffix.
var corepackVersion = regexp.MustCompile(`^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*|sha(?:224|256|384|512)\.[A-Za-z0-9+/=]+))?$`)

// validCorepackVersion ensures prerelease numeric identifiers follow SemVer:
// unlike build metadata, numeric prerelease identifiers cannot have leading zeros.
func validCorepackVersion(version string) bool {
	if !corepackVersion.MatchString(version) {
		return false
	}
	release, _, _ := strings.Cut(version, "+")
	_, prerelease, hasPrerelease := strings.Cut(release, "-")
	if !hasPrerelease {
		return true
	}
	for _, identifier := range strings.Split(prerelease, ".") {
		if len(identifier) < 2 || identifier[0] != '0' {
			continue
		}
		numeric := true
		for i := 1; i < len(identifier); i++ {
			if identifier[i] < '0' || identifier[i] > '9' {
				numeric = false
				break
			}
		}
		if numeric {
			return false
		}
	}
	return true
}

// selectNodePackageManager chooses a known executable from packageManager
// metadata while detecting stale lockfiles. It never executes the value.
func selectNodePackageManager(declared, detected string, lockfiles []string) (string, []Finding) {
	if declared == "" {
		return detected, nil
	}
	name, version, ok := strings.Cut(declared, "@")
	if !ok || len(version) == 0 || len(version) > 128 || !validCorepackVersion(version) ||
		(name != "npm" && name != "pnpm" && name != "yarn" && name != "bun") {
		return detected, []Finding{{
			Level: "warning", Code: "package-manager-invalid",
			Message: "package.json has an unsupported or malformed packageManager declaration",
			Remedy:  "Use npm@version, pnpm@version, yarn@version, or bun@version.",
		}}
	}

	var mismatched []string
	for _, file := range lockfiles {
		owner := "npm"
		switch file {
		case "pnpm-lock.yaml":
			owner = "pnpm"
		case "yarn.lock":
			owner = "yarn"
		case "bun.lock", "bun.lockb":
			owner = "bun"
		}
		if owner != name {
			mismatched = append(mismatched, file)
		}
	}
	if len(mismatched) == 0 {
		return name, nil
	}
	sort.Strings(mismatched)
	return name, []Finding{{
		Level: "warning", Code: "package-manager-lock-mismatch",
		Message: fmt.Sprintf("packageManager selects %s but incompatible lockfiles exist: %s", name, strings.Join(mismatched, ", ")),
		Remedy:  "Regenerate lockfiles using the declared package manager and remove stale ones.",
	}}
}
