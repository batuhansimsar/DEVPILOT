package doctor

// declaredNodeManager uses the same strict Corepack version validation as
// selectNodePackageManager. Invalid declarations must not influence which
// package-manager executable is selected for an inspected project.
func declaredNodeManager(spec string) string {
	manager, findings := selectNodePackageManager(spec, "", nil)
	if len(findings) != 0 {
		return ""
	}
	return manager
}
