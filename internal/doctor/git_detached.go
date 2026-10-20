package doctor

// isGitDetachedHead recognizes an object ID in .git/HEAD without invoking git.
// HEAD is untrusted workspace input: its length alone must not be interpreted
// as a detached commit, and unexpected whitespace must not be accepted.
func isGitDetachedHead(data []byte) bool {
	if len(data) > 0 && data[len(data)-1] == '\n' {
		data = data[:len(data)-1]
	}
	if len(data) > 0 && data[len(data)-1] == '\r' {
		data = data[:len(data)-1]
	}
	if len(data) != 40 && len(data) != 64 {
		return false
	}
	for _, b := range data {
		if !((b >= '0' && b <= '9') || (b >= 'a' && b <= 'f') || (b >= 'A' && b <= 'F')) {
			return false
		}
	}
	return true
}
