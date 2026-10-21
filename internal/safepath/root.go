// Package safepath protects directory scans from symbolic-link redirection.
package safepath

import (
	"errors"
	"os"
	"path/filepath"
	"runtime"
)

// ErrLinkedPath indicates that the selected directory or one of its ancestors
// is a symbolic link. The error does not reveal filesystem paths.
var ErrLinkedPath = errors.New("project path contains a symbolic link")

// EnsureUnlinkedPath checks every component of an absolute scan path, including
// its ancestors. Callers must subsequently use that same absolute path for
// filesystem operations, rather than the original uncleaned user input.
//
// On macOS, /tmp, /var and /etc are standard root-level aliases pointing into
// /private. Those specific aliases are permitted if they resolve to the
// conventional targets, matching the Python scanner's root policy.
func EnsureUnlinkedPath(abs string) error {
	if !filepath.IsAbs(abs) || filepath.Clean(abs) != abs {
		return errors.New("project path must be absolute and clean")
	}
	filesystemRoot := filepath.VolumeName(abs) + string(filepath.Separator)
	for current := abs; ; current = filepath.Dir(current) {
		info, err := os.Lstat(current)
		if err != nil {
			return errors.New("cannot inspect project path component")
		}
		if info.Mode()&os.ModeSymlink != 0 && !allowedMacOSAlias(current, abs, filesystemRoot) {
			return ErrLinkedPath
		}
		if current == filesystemRoot {
			break
		}
	}
	return nil
}

func allowedMacOSAlias(current, selected, filesystemRoot string) bool {
	if runtime.GOOS != "darwin" || filesystemRoot != "/" ||
		current == selected || filepath.Dir(current) != "/" {
		return false
	}
	name := filepath.Base(current)
	if name != "tmp" && name != "var" && name != "etc" {
		return false
	}
	resolved, err := filepath.EvalSymlinks(current)
	return err == nil && resolved == filepath.Join("/private", name)
}
