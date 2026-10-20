// Package tree builds a bounded, read-only map of an unfamiliar workspace.
package tree

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

type Entry struct {
	Path  string `json:"path"`
	Depth int    `json:"depth"`
	Kind  string `json:"kind"`
}
type Report struct {
	Root      string  `json:"root"`
	Entries   []Entry `json:"entries"`
	Truncated bool    `json:"truncated"`
}

var stop = errors.New("entry limit reached")

// Inspect does not follow symbolic links, execute code, or read file contents.
// It excludes generated/dependency directories, but includes config files.
func Inspect(path string, depth, maxEntries int) (Report, error) {
	if depth < 1 || depth > 10 {
		return Report{}, errors.New("depth must be between 1 and 10")
	}
	if maxEntries < 1 || maxEntries > 2000 {
		return Report{}, errors.New("max entries must be between 1 and 2000")
	}
	root, err := filepath.Abs(path)
	if err != nil {
		return Report{}, err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return Report{}, fmt.Errorf("resolve root: %w", err)
	}
	stat, err := os.Stat(root)
	if err != nil {
		return Report{}, fmt.Errorf("open workspace: %w", err)
	}
	if !stat.IsDir() {
		return Report{}, errors.New("workspace must be a directory")
	}
	report := Report{Root: root, Entries: []Entry{}}
	err = filepath.WalkDir(root, func(p string, e fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return fmt.Errorf("read %q: %w", p, walkErr)
		}
		if p == root {
			return nil
		}
		rel, err := filepath.Rel(root, p)
		if err != nil {
			return err
		}
		level := strings.Count(filepath.ToSlash(rel), "/") + 1
		if e.IsDir() {
			if ignored(e.Name()) || level > depth {
				return filepath.SkipDir
			}
		} else if level > depth {
			return nil
		}
		if len(report.Entries) >= maxEntries {
			report.Truncated = true
			return stop
		}
		kind := "file"
		if e.IsDir() {
			kind = "directory"
		} else if e.Type()&os.ModeSymlink != 0 {
			kind = "symlink"
		}
		report.Entries = append(report.Entries, Entry{Path: filepath.ToSlash(rel), Depth: level, Kind: kind})
		return nil
	})
	if errors.Is(err, stop) {
		return report, nil
	}
	return report, err
}
func ignored(s string) bool {
	switch s {
	case ".git", "node_modules", "vendor", ".venv", "venv", "__pycache__", "dist", "build", "target", ".next", ".cache", "coverage", "bin", "obj", ".tox":
		return true
	}
	return false
}
