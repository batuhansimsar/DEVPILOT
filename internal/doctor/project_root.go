package doctor

import (
	"errors"
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
		return "", errors.New("cannot resolve project directory")
	}
	st, err := os.Lstat(abs)
	if err != nil {
		// os.PathError embeds the full user-supplied path. Do not echo it into
		// CLI diagnostics, where it can reveal locations or inject control text.
		switch {
		case errors.Is(err, os.ErrNotExist):
			return "", fmt.Errorf("project directory: %w", os.ErrNotExist)
		case errors.Is(err, os.ErrPermission):
			return "", fmt.Errorf("project directory: %w", os.ErrPermission)
		default:
			return "", errors.New("cannot inspect project directory")
		}
	}
	if st.Mode()&os.ModeSymlink != 0 {
		return "", fmt.Errorf("project directory must not be a symbolic link")
	}
	if !st.IsDir() {
		return "", fmt.Errorf("project path is not a directory")
	}
	if err := safepath.EnsureUnlinkedPath(abs); err != nil {
		return "", err
	}
	return abs, nil
}
