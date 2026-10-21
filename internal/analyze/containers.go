package analyze

// isContainerConfig uses the same filename rules as manifest inventory so
// inspect reports never disagree about which container files were discovered.
func isContainerConfig(name string) bool {
	_, ok := dockerManifestKind(name)
	return ok
}
