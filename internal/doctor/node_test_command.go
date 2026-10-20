package doctor

// nodeTestArgs selects the package-script invocation, not a tool's built-in
// test runner. In particular, `bun test` does not invoke package.json scripts.
func nodeTestArgs(executable string) []string {
	if executable == "bun" {
		return []string{"run", "test"}
	}
	return []string{"test"}
}
