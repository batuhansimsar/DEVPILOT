// Package tree provides a bounded, read-only project structure overview.
package tree

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

const MaxEntries = 5000
const MaxDepth = 12

// Entry is a repository-relative path; it never includes file contents.
type Entry struct {
	Path string `json:"path"`
	Type string `json:"type"`
}

type Report struct {
	Root      string  `json:"root"`
	Entries   []Entry `json:"entries"`
	Truncated bool    `json:"truncated"`
}

// Scan enumerates a directory tree without following symlinks or opening files.
// Common generated directories and sensitive local configuration filenames are excluded.
func Scan(path string, depth int) (Report, error) {
	if depth < 0 || depth > MaxDepth {
		return Report{}, fmt.Errorf("depth must be between 0 and %d", MaxDepth)
	}
	root, err := filepath.Abs(path)
	if err != nil {
		return Report{}, err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return Report{}, err
	}
	st, err := os.Stat(root)
	if err != nil {
		return Report{}, err
	}
	if !st.IsDir() {
		return Report{}, errors.New("project path is not a directory")
	}
	r := Report{Root: root, Entries: []Entry{}}
	err = filepath.WalkDir(root, func(full string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return fmt.Errorf("read %s: %w", filepath.Base(full), walkErr)
		}
		if full == root {
			return nil
		}
		rel, err := filepath.Rel(root, full)
		if err != nil {
			return err
		}
		dpth := len(strings.Split(rel, string(filepath.Separator)))
		if exclude(d.Name()) || d.Type()&os.ModeSymlink != 0 {
			if d.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}
		if dpth > depth {
			if d.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}
		if len(r.Entries) >= MaxEntries {
			r.Truncated = true
			return filepath.SkipAll
		}
		typ := "file"
		if d.IsDir() {
			typ = "directory"
		}
		r.Entries = append(r.Entries, Entry{Path: filepath.ToSlash(rel), Type: typ})
		if d.IsDir() && dpth == depth {
			return filepath.SkipDir
		}
		return nil
	})
	if err != nil {
		return Report{}, err
	}
	sort.Slice(r.Entries, func(i, j int) bool { return r.Entries[i].Path < r.Entries[j].Path })
	return r, nil
}

func exclude(name string) bool {
	if name == ".env" || strings.HasPrefix(name, ".env.") {
		return true
	}
	switch name {
	case ".git", "node_modules", "vendor", "dist", "build", "target", ".next", ".venv", "venv", "__pycache__", "coverage", ".idea", ".turbo", ".cache":
		return true
	}
	return false
}

// Render writes a human-readable hierarchy. Structure only; never file contents.
func Render(w io.Writer, r Report) {
	fmt.Fprintf(w, "Project tree: %s\n.\n", r.Root)
	children := map[string][]Entry{}
	for _, entry := range r.Entries {
		parent := filepath.ToSlash(filepath.Dir(entry.Path))
		children[parent] = append(children[parent], entry)
	}
	var render func(string, string)
	render = func(parent, prefix string) {
		items := children[parent]
		for i, item := range items {
			last := i == len(items)-1
			arm := "├── "
			nestedPrefix := prefix + "│   "
			if last {
				arm = "└── "
				nestedPrefix = prefix + "    "
			}
			name := filepath.Base(item.Path)
			if item.Type == "directory" {
				name += "/"
			}
			fmt.Fprintln(w, prefix+arm+name)
			if item.Type == "directory" {
				render(item.Path, nestedPrefix)
			}
		}
	}
	render(".", "")
	if r.Truncated {
		fmt.Fprintf(w, "... truncated at %d entries\n", MaxEntries)
	}
}

// Run parses the tree subcommand. It is safe for unknown workspaces because it
// never executes project scripts and only enumerates file metadata.
func Run(args []string, stdout, stderr io.Writer) int {
	f := flag.NewFlagSet("tree", flag.ContinueOnError)
	f.SetOutput(stderr)
	depth := f.Int("depth", 4, "maximum directory depth (0-12)")
	asJSON := f.Bool("json", false, "machine-readable JSON output")
	if err := f.Parse(args); err != nil {
		return 2
	}
	if f.NArg() > 1 {
		fmt.Fprintln(stderr, "tree accepts at most one directory path")
		return 2
	}
	path := "."
	if f.NArg() == 1 {
		path = f.Arg(0)
	}
	report, err := Scan(path, *depth)
	if err != nil {
		fmt.Fprintln(stderr, "tree:", err)
		return 2
	}
	if *asJSON {
		encoder := json.NewEncoder(stdout)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(report); err != nil {
			fmt.Fprintln(stderr, "tree:", err)
			return 1
		}
	}
	if !*asJSON {
		Render(stdout, report)
	}
	return 0
}
