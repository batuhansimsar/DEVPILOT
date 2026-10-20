// Package projecttree builds a bounded, read-only view of a workspace.
// It never follows directory symlinks or executes repository code.
package projecttree

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// Options limit how much of an untrusted repository is inspected.
type Options struct {
	MaxDepth   int
	MaxEntries int
	ShowHidden bool
}

type Entry struct {
	Path  string `json:"path"`
	Kind  string `json:"kind"`
	Depth int    `json:"depth"`
}

type Result struct {
	Root      string   `json:"root"`
	Entries   []Entry  `json:"entries"`
	Truncated bool     `json:"truncated"`
	Skipped   []string `json:"skipped"`
}

var skipDirectories = map[string]bool{
	".git": true, "node_modules": true, "vendor": true, "dist": true, "build": true,
	".next": true, ".venv": true, "venv": true, "__pycache__": true, "target": true,
	".idea": true, ".gradle": true, "bin": true, "obj": true,
}

// Scan starts at the selected root and returns path names only, never file contents.
// Symlinked directories are described as symlinks but never traversed.
func Scan(root string, opts Options) (Result, error) {
	if opts.MaxDepth < 0 || opts.MaxDepth > 20 {
		return Result{}, errors.New("max depth must be between 0 and 20")
	}
	if opts.MaxEntries < 1 || opts.MaxEntries > 10000 {
		return Result{}, errors.New("max entries must be between 1 and 10000")
	}
	abs, err := filepath.Abs(root)
	if err != nil {
		return Result{}, err
	}
	st, err := os.Lstat(abs)
	if err != nil {
		return Result{}, fmt.Errorf("workspace: %w", err)
	}
	if !st.IsDir() {
		return Result{}, fmt.Errorf("workspace is not a directory: %s", abs)
	}
	r := Result{Root: abs, Entries: []Entry{}, Skipped: []string{}}
	var visit func(string, int) error
	visit = func(dir string, depth int) error {
		children, e := os.ReadDir(dir)
		if e != nil {
			if dir == abs {
				return fmt.Errorf("list workspace: %w", e)
			}
			r.Skipped = append(r.Skipped, "unreadable directory: "+rel(abs, dir))
			return nil
		}
		sort.Slice(children, func(i, j int) bool { return children[i].Name() < children[j].Name() })
		for _, child := range children {
			name := child.Name()
			if !opts.ShowHidden && strings.HasPrefix(name, ".") {
				continue
			}
			path := filepath.Join(dir, name)
			if len(r.Entries) >= opts.MaxEntries {
				r.Truncated = true
				return nil
			}
			kind := "file"
			mode := child.Type()
			if mode&fs.ModeSymlink != 0 {
				kind = "symlink"
			} else if mode.IsDir() {
				kind = "directory"
			} else if !mode.IsRegular() {
				kind = "other"
			}
			r.Entries = append(r.Entries, Entry{Path: rel(abs, path), Kind: kind, Depth: depth})
			if kind == "directory" && !skipDirectories[name] {
				if depth < opts.MaxDepth {
					if e := visit(path, depth+1); e != nil {
						return e
					}
					if r.Truncated {
						return nil
					}
				}
			}
		}
		return nil
	}
	if e := visit(abs, 0); e != nil {
		return Result{}, e
	}
	return r, nil
}
func rel(root, path string) string { v, _ := filepath.Rel(root, path); return filepath.ToSlash(v) }
