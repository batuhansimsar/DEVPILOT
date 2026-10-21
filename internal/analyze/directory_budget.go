package analyze

// MaxDirectories limits visits to non-ignored subdirectories during analysis.
// The file limit alone does not bound scans of directory-only workspaces.
const MaxDirectories = 20000

// directoryBudget counts scanned directories, excluding the root and directories
// already skipped by the ignore list. It prevents deep/wide empty trees from
// consuming unbounded traversal time.
type directoryBudget struct {
	visited int
}

func (b *directoryBudget) allow() bool {
	if b.visited >= MaxDirectories {
		return false
	}
	b.visited++
	return true
}
