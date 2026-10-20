// Package projecttree creates a bounded, read-only view of project structure.
package projecttree

import (
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"unicode"
)

const MaxEntries = 4000
const MaxDepth = 6

// Entry only contains names/types, never the contents of project files.
type Entry struct {
	Path string `json:"path"`
	Kind string `json:"kind"` // directory, file, symlink
}

type Result struct {
	Root      string  `json:"root"`
	Depth     int     `json:"depth"`
	Entries   []Entry `json:"entries"`
	Truncated bool    `json:"truncated"`
}

var skip = map[string]bool{
	".git": true, "node_modules": true, "vendor": true, "dist": true,
	"build": true, "target": true, ".venv": true, "venv": true,
	"__pycache__": true, ".next": true, ".turbo": true, "coverage": true,
	"bin": true, "obj": true,
}
var errLimit = errors.New("project tree limit reached")

// Scan does not follow directory symlinks and never opens any project file.
// All results are bounded by depth and entry count to avoid runaway traversal.
func Scan(root string, depth int) (Result, error) {
	if depth < 1 || depth > MaxDepth {
		return Result{}, fmt.Errorf("depth must be between 1 and %d", MaxDepth)
	}
	if root == "" {
		root = "."
	}
	abs, err := filepath.Abs(root)
	if err != nil {
		return Result{}, err
	}
	abs, err = filepath.EvalSymlinks(abs)
	if err != nil {
		return Result{}, fmt.Errorf("workspace: %w", err)
	}
	stat, err := os.Stat(abs)
	if err != nil {
		return Result{}, err
	}
	if !stat.IsDir() {
		return Result{}, errors.New("workspace must be a directory")
	}
	result := Result{Root: abs, Depth: depth, Entries: []Entry{}}
	err = filepath.WalkDir(abs, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return fmt.Errorf("inspect %q: %w", path, walkErr)
		}
		if path == abs {
			return nil
		}
		rel, err := filepath.Rel(abs, path)
		if err != nil {
			return err
		}
		level := len(strings.Split(rel, string(filepath.Separator)))
		if level > depth {
			if entry.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}
		if entry.IsDir() && skip[entry.Name()] {
			return filepath.SkipDir
		}
		if len(result.Entries) >= MaxEntries {
			result.Truncated = true
			return errLimit
		}
		kind := "file"
		if entry.IsDir() {
			kind = "directory"
		} else if entry.Type()&os.ModeSymlink != 0 {
			kind = "symlink"
		}
		result.Entries = append(result.Entries, Entry{Path: filepath.ToSlash(rel), Kind: kind})
		if entry.IsDir() && level >= depth {
			return filepath.SkipDir
		}
		return nil
	})
	if errors.Is(err, errLimit) {
		return result, nil
	}
	if err != nil {
		return Result{}, err
	}
	return result, nil
}

// Print emits an approachable, deterministic outline for terminal use.
func Print(w io.Writer, tree Result) error {
	if _, err := fmt.Fprintf(w, "DevPilot tree: %s (depth %d)\n", tree.Root, tree.Depth); err != nil {
		return err
	}
	for _, item := range tree.Entries {
		level := strings.Count(item.Path, "/")
		suffix := ""
		if item.Kind == "directory" {
			suffix = "/"
		} else if item.Kind == "symlink" {
			suffix = " -> [symlink, not followed]"
		}
		if _, err := fmt.Fprintf(w, "%s- %s%s\n", strings.Repeat("  ", level), safeDisplayName(filepath.Base(filepath.FromSlash(item.Path))), suffix); err != nil {
			return err
		}
	}
	if tree.Truncated {
		_, err := fmt.Fprintf(w, "... output limited to %d entries\n", MaxEntries)
		return err
	}
	return nil
}


// safeDisplayName prevents control sequences and bidirectional format characters
// in repository-supplied filenames from changing terminal output.
func safeDisplayName(name string) string {
	return strings.Map(func(r rune) rune {
		if unicode.IsControl(r) || unicode.Is(unicode.Cf, r) {
			return '?'
		}
		return r
	}, name)
}
