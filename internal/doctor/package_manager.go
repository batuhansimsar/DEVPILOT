package doctor

import "strings"

// declaredNodeManager recognizes the packageManager field used by Corepack.
// Unsupported or malformed identifiers are ignored instead of becoming a
// program name, so project metadata cannot inject arbitrary executables.
func declaredNodeManager(spec string) string {
	name, version, ok := strings.Cut(spec, "@")
	if !ok || version == "" || strings.ContainsAny(version, " \t\r\n") {
		return ""
	}
	switch name {
	case "npm", "pnpm", "yarn", "bun":
		return name
	default:
		return ""
	}
}
