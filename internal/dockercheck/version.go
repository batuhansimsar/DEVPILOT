package dockercheck

// validDockerServerVersion accepts Docker's single-line version identifiers
// while rejecting terminal control sequences, binary data, and oversized
// unexpected output from a substituted Docker CLI or daemon.
// Separators must occur singly between alphanumeric components: malformed
// versions must not be mistaken for a reachable Docker daemon.
func validDockerServerVersion(version string) bool {
	if len(version) == 0 || len(version) > 128 {
		return false
	}
	previousSeparator := false
	for i := 0; i < len(version); i++ {
		c := version[i]
		if c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' {
			previousSeparator = false
			continue
		}
		if i > 0 && i < len(version)-1 && !previousSeparator &&
			(c == '.' || c == '-' || c == '_' || c == '+') {
			previousSeparator = true
			continue
		}
		return false
	}
	return true
}
