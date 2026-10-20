package doctor

// detectJSLockfiles discovers JavaScript package-manager lockfiles without
// opening or executing anything from the inspected project. The first match
// determines the tool, preserving the existing deterministic precedence.
func detectJSLockfiles(root string) (manager, executable string, files []string) {
	manager, executable = "npm", "npm"
	for _, spec := range []struct {
		file, manager, exe string
	}{
		{"pnpm-lock.yaml", "pnpm", "pnpm"},
		{"yarn.lock", "yarn", "yarn"},
		{"bun.lock", "bun", "bun"},
		{"bun.lockb", "bun", "bun"},
		{"package-lock.json", "npm", "npm"},
		{"npm-shrinkwrap.json", "npm", "npm"},
	} {
		if !hasMarker(root, spec.file) {
			continue
		}
		if len(files) == 0 {
			manager, executable = spec.manager, spec.exe
		}
		files = append(files, spec.file)
	}
	return manager, executable, files
}
