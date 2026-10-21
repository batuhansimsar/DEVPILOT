package analyze

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"

	"github.com/batuhansimsar/DEVPILOT/internal/safepath"
)

// projectRoot validates the explicitly selected directory without following
// symlinks at the root or in its ancestors. Filesystem diagnostics are
// sanitized to avoid exposing workspace paths or terminal control sequences.
func projectRoot(path string) (string, error) {
	root, err := filepath.Abs(path)
	if err != nil {
		return "", errors.New("cannot resolve project directory")
	}
	info, err := os.Lstat(root)
	if err != nil {
		// PathError.Error() includes the untrusted absolute path. Return only
		// a stable error class, keeping errors.Is useful for callers.
		switch {
		case errors.Is(err, os.ErrNotExist):
			return "", fmt.Errorf("project directory: %w", os.ErrNotExist)
		case errors.Is(err, os.ErrPermission):
			return "", fmt.Errorf("project directory: %w", os.ErrPermission)
		default:
			return "", errors.New("cannot inspect project directory")
		}
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return "", errors.New("project directory is a symbolic link")
	}
	if !info.IsDir() {
		return "", errors.New("project path is not a directory")
	}
	if err := safepath.EnsureUnlinkedPath(root); err != nil {
		return "", err
	}
	return root, nil
}
