// Package projecttree maps a project's directory layout without executing code
// or following symbolic links. It bounds traversal and reports truncation.
package projecttree

import (
	"errors'
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

const (
	DefaultDepth = 3
	MaxDepth     = 8
	MaxEntries   = 2000
)

// Entry is a single repository-relative name, never file contents.
type Entry struct {
	Path  string `json:"path"`
	Type  string `json:"type"` // file, directory, symlink, other
	Depth int    `json:"depth"`
}

type Map struct {
	Root               string   `json:"root"`
	Entries            []Entry  `json:"entries"`
	SkippedDirectories []string `json:"skipped_directories"`
	Warnings           []string `json:"warnings"`
	Truncated          bool     `json:"truncated"`
}

// MapDirectory lists directory names up to maxDepth (1..8) and 2,000 entries.
// It excludes common generated and private tooling directories, avoids reading
// file contents, and never intentionally follows symlinks. The output is not a
// security boundary against a concurrently mutating filesystem.
func MapDirectory(path string, maxDepth int) (Map, error) {
	if maxDepth < 1 || maxDepth > MaxDepth {
		return Map{}, fmt.Errorf("depth must be between 1 and %d", MaxDepth)
	}
	root, err := filepath.Abs(path)
	if err != nil {
		return Map{}, fmt.Errorf("resolve root: %w", err)
	}
	rootInfo, err := os.Lstat(root)
	if err != nil {
		return Map{}, fmt.Errorf("read root: %w", err)
	}
	if !rootInfo.IsDir() {
		return Map{}, fmt.Errorf("root must be a real directory (not a file or symlink)")
	}
	result := Map{Root: root, Entries: []Entry{}, SkippedDirectories: []string{}, Warnings: []string{}}
	var walk func(string, int)
	walk = func(relative string, depth int) {
		if result.Truncated {
			return
		}
		absolute := filepath.Join(root, relative)
		// The real path is supplied by the user; nested symlink entries are
		// recognized before recursion and deliberately never traversed.
		dir, err := os.Open(absolute)
		if err != nil {
			result.Warnings = append(result.Warnings, fmt.Sprintf("Cannot open directory %q: %v", relative, err))
			return
		}
		defer dir.Close()
		// Read a bounded batch. Excess entries are signalled, not silently lost.
		children, err := dir.ReadDir(MaxEntries + 1)
		if err != nil && !errors.Is(err, io.EOF) {
			result.Warnings = append(result.Warnings, fmt.Sprintf("Cannot list directory %q: %v", relative, err))
			return
		}
		if len(children) > MaxEntries {
			result.Truncated = true
			children = children[:MaxEntries]
		}
		sort.Slice(children, func(i, j int) bool { return children[i].Name() < children[j].Name() })
		for _, child := range children {
			if len(result.Entries) >= MaxEntries {
				result.Truncated = true
				return
			}
			name := child.Name()
			newRelative := filepath.Join(relative, name)
			display := filepath.ToSlash(newRelative)
			if child.IsDir() && ignoredDirectory(name) {
				result.SkippedDirectories = append(result.SkippedDirectories, display)
				continue
			}
			kind := "file"
			if child.Type()&os.ModeSymlink != 0 {
				kind = "symlink"
			} else if child.IsDir() {
				kind = "directory"
			} else if !child.Type().IsRegular() {
				kind = "other"
			}
			result.Entries = append(result.Entries, Entry{Path: display, Type: kind, Depth: depth})
			if kind == "directory" && depth < maxDepth {
				walk(newRelative, depth+1)
			}
		}
	}
	walk(".", 1)
	sort.Strings(result.SkippedDirectories)
	return result, nil
}

func ignoredDirectory(name string) bool {
	switch strings.ToLower(name) {
	case ".git", "node_modules", ".venv", "venv", "vendor", "dist", "build", "target", ".next", ".idea", ".gradle", "__pycache__", ".turbo", "bin", "obj":
		return true
	default:
		return false
	}
}
