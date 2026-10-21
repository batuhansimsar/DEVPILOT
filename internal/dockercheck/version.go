package dockercheck

// validDockerServerVersion accepts Docker's single-line version identifiers
// while rejecting terminal control sequences, binary data, and oversized
// unexpected output from a substituted Docker CLI or daemon.
func validDockerServerVersion(version string) bool {
	if len(version) == 0 || len(version) > 128 {
		return false
	}
	for i := 0; i < len(version); i++ {
		c := version[i]
		if c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' {
			continue
		}
		if i > 0 && (c == '.' || c == '-' || c == '_' || c == '+') {
			continue
		}
		return false
	}
	return true
}
