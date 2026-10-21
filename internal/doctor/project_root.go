package doctor

import (
	"fmt"
	"os"
	"path/filepath"
)

// validateProjectRoot resolves an absolute path without following a symbolic
// link at the selected project root. This keeps doctor consistent with analyze
// and avoids inspecting an unexpected directory outside the chosen workspace.
func validateProjectRoot(path string) (string, error) {
	abs, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}
	st, err := os.Lstat(abs)
	if err != nil {
		return "", fmt.Errorf("project directory: %w", err)
	}
	if st.Mode()&os.ModeSymlink != 0 {
		return "", fmt.Errorf("project directory must not be a symbolic link")
	}
	if !st.IsDir() {
		return "", fmt.Errorf("project path is not a directory: %s", abs)
	}
	return abs, nil
}
