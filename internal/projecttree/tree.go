// Package projecttree builds bounded, read-only project structure summaries.
package projecttree

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Entry represents a relative path without exposing file contents or symlink targets.
type Entry struct {
	Path  string `json:"path"`
	Kind  string `json:"kind"`
	Depth int    `json:"depth"`
}

// Result is safe to serialize directly as JSON.
type Result struct {
	Root      string  `json:"root"`
	Entries   []Entry `json:"entries"`
	Truncated bool    `json:"truncated"`
}

var skipDirectories = map[string]bool{
	".git": true, ".hg": true, ".svn": true, "node_modules": true,
	"vendor": true, ".venv": true, "venv": true, "__pycache__": true,
	".next": true, "dist": true, "build": true, ".idea": true,
}

func privateName(name string) bool {
	lower := strings.ToLower(name)
	if lower == ".env" || strings.HasPrefix(lower, ".env.") {
		return true
	}
	if strings.HasSuffix(lower, ".pem") || strings.HasSuffix(lower, ".key") || strings.HasSuffix(lower, ".p12") {
		return true
	}
	switch lower {
	case "id_rsa", "id_ed25519", "credentials.json", "secrets.json":
		return true
	}
	return false
}

// Scan never follows symlinks, never executes code, and enforces hard bounds.
// maxDepth counts components below root, where 1 lists only root children.
func Scan(path string, maxDepth, maxEntries int) (Result, error) {
	if maxDepth < 1 || maxDepth > 10 {
		return Result{}, fmt.Errorf("depth must be between 1 and 10")
	}
	if maxEntries < 1 || maxEntries > 2000 {
		return Result{}, fmt.Errorf("max entries must be between 1 and 2000")
	}
	root, err := filepath.Abs(path)
	if err != nil {
		return Result{}, err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return Result{}, fmt.Errorf("resolve project path: %w", err)
	}
	stat, err := os.Stat(root)
	if err != nil {
		return Result{}, err
	}
	if !stat.IsDir() {
		return Result{}, fmt.Errorf("not a directory: %s", root)
	}
	result := Result{Root: root, Entries: []Entry{}}
	var visit func(string, int) error
	visit = func(dir string, depth int) error {
		children, err := os.ReadDir(dir)
		if err != nil {
			return fmt.Errorf("inspect %s: %w", dir, err)
		}
		for _, child := range children {
			name := child.Name()
			if privateName(name) {
				continue
			}
			info, err := child.Info()
			if err != nil {
				return fmt.Errorf("inspect %s: %w", name, err)
			}
			if info.IsDir() && skipDirectories[name] {
				continue
			}
			if len(result.Entries) >= maxEntries {
				result.Truncated = true
				return nil
			}
			full := filepath.Join(dir, name)
			relative, err := filepath.Rel(root, full)
			if err != nil {
				return err
			}
			kind := "file"
			if info.Mode()&os.ModeSymlink != 0 {
				kind = "symlink"
			} else if info.IsDir() {
				kind = "dir"
			}
			result.Entries = append(result.Entries, Entry{Path: filepath.ToSlash(relative), Kind: kind, Depth: depth})
			if kind == "dir" && depth < maxDepth {
				if err := visit(full, depth+1); err != nil {
					return err
				}
				if result.Truncated {
					return nil
				}
			}
		}
		return nil
	}
	if err := visit(root, 1); err != nil {
		return Result{}, err
	}
	return result, nil
}
