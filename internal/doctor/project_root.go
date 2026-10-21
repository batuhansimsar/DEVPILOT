package doctor

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/batuhansimsar/DEVPILOT/internal/safepath"
)

// validateProjectRoot rejects symbolic links at the selected directory or in
// its ancestors, preventing checks from escaping the intended workspace.
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
	if err := safepath.EnsureUnlinkedPath(abs); err != nil {
		return "", err
	}
	return abs, nil
}
