// Package pathguard checks filesystem ancestors before project inspection.
package pathguard

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

// ValidateAncestors rejects symlinks above a selected project root.
// Lstat on the selected root alone is insufficient: it follows links in
// ancestor directories, allowing inspection outside the intended workspace.
// The caller is responsible for checking that the root itself is unlinked.
func ValidateAncestors(absolutePath string) error {
	for parent := filepath.Dir(absolutePath); ; parent = filepath.Dir(parent) {
		info, err := os.Lstat(parent)
		if err != nil {
			return fmt.Errorf("cannot inspect project path ancestor: %w", err)
		}
		if info.Mode()&os.ModeSymlink != 0 && !macOSSystemAlias(parent) {
			return errors.New("project path contains a symbolic-link ancestor")
		}
		if filepath.Dir(parent) == parent {
			return nil
		}
	}
}

// macOS exposes /etc, /tmp and /var as conventional links into /private.
// Permit only these exact system aliases, not arbitrary workspace links.
func macOSSystemAlias(path string) bool {
	if runtime.GOOS != "darwin" || filepath.Dir(path) != string(filepath.Separator) {
		return false
	}
	name := filepath.Base(path)
	if name != "etc" && name != "tmp" && name != "var" {
		return false
	}
	resolved, err := filepath.EvalSymlinks(path)
	return err == nil && resolved == filepath.Join(string(filepath.Separator), "private", name)
}
