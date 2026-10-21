package analyze

import (
	"fmt"
	"os"
	"path/filepath"
)

// projectRoot validates the explicitly selected directory without following a
// symlink at the requested root. WalkDir itself will skip symlinks below root.
func projectRoot(path string) (string, error) {
	root, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}
	info, err := os.Lstat(root)
	if err != nil {
		return "", fmt.Errorf("project directory: %w", err)
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return "", fmt.Errorf("project directory is a symbolic link")
	}
	if !info.IsDir() {
		return "", fmt.Errorf("not a directory: %s", root)
	}
	return root, nil
}
