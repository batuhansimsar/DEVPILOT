package doctor

import (
	"fmt"
	"sort"
	"strings"
)

// selectNodePackageManager chooses a known executable from packageManager
// metadata while detecting stale lockfiles. It never executes the value.
func selectNodePackageManager(declared, detected string, lockfiles []string) (string, []Finding) {
	if declared == "" {
		return detected, nil
	}
	name, version, ok := strings.Cut(declared, "@")
	if !ok || version == "" || len(version) > 128 || strings.ContainsAny(version, " \t\r\n") ||
		(name != "npm" && name != "pnpm" && name != "yarn" && name != "bun") {
		return detected, []Finding{{
			Level: "warning", Code: "package-manager-invalid",
			Message: "package.json has an unsupported or malformed packageManager declaration",
			Remedy: "Use npm@version, pnpm@version, yarn@version, or bun@version.",
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
		Remedy: "Regenerate lockfiles using the declared package manager and remove stale ones.",
	}}
}
