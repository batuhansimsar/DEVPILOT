package analyze

import (
	"errors"
	"io/fs"
	"path/filepath"
	"strconv"
	"strings"
)

// walkWarning describes a filesystem scan failure without exposing the raw
// error, which can contain absolute paths or sensitive OS/provider details.
// Quoting the relative path also prevents control characters and bidirectional
// Unicode formatting from being interpreted by terminals or log viewers.
func walkWarning(root, current string, walkErr error) string {
	rel, err := filepath.Rel(root, current)
	if err != nil || filepath.IsAbs(rel) || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		rel = "."
	}

	cause := "filesystem error"
	switch {
	case errors.Is(walkErr, fs.ErrPermission):
		cause = "permission denied"
	case errors.Is(walkErr, fs.ErrNotExist):
		cause = "path no longer exists"
	}
	return "Cannot inspect " + strconv.QuoteToASCII(filepath.ToSlash(rel)) + ": " + cause
}
