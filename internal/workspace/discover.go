// Package workspace discovers project boundaries in monorepos without running code.
// Files inside symlinks, dependency directories, and generated outputs are not traversed.
package workspace

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
)

const (
	maxScanEntries = 12000
	maxProjects    = 256
	maxDepth       = 4 // root is depth 0
)

var errLimit = errors.New("workspace safety limit reached")

type Project struct {
	Path    string        `json:"path"` // relative to the workspace root
	Markers []string      `json:"markers"`
	Report  doctor.Report `json:"report"`
}

type Map struct {
	Workspace       string    `json:"workspace"`
	Projects        []Project `json:"projects"`
	ScannedEntries  int       `json:"scanned_entries"`
	SkippedSymlinks int       `json:"skipped_symlinks"`
	Truncated       bool      `json:"truncated"`
	ScanErrors      []string  `json:"scan_errors"`
}

func Discover(root string) (Map, error) {
	abs, err := filepath.Abs(root)
	if err != nil {
		return Map{}, fmt.Errorf("resolve workspace: %w", err)
	}
	abs, err = filepath.EvalSymlinks(abs)
	if err != nil {
		return Map{}, fmt.Errorf("access workspace: %w", err)
	}
	info, err := os.Stat(abs)
	if err != nil {
		return Map{}, fmt.Errorf("stat workspace: %w", err)
	}
	if !info.IsDir() {
		return Map{}, fmt.Errorf("workspace is not a directory: %s", abs)
	}
	result := Map{Workspace: abs, Projects: []Project{}, ScanErrors: []string{}}
	markers := make(map[string]map[string]bool)
	err = filepath.WalkDir(abs, func(path string, entry fs.DirEntry, walkErr error) error {
		rel, relErr := filepath.Rel(abs, path)
		if relErr != nil {
			return relErr
		}
		slashRel := filepath.ToSlash(rel)
		if walkErr != nil {
			result.ScanErrors = append(result.ScanErrors, fmt.Sprintf("%s: %v", slashRel, walkErr))
			return nil
		}
		result.ScannedEntries++
		if result.ScannedEntries > maxScanEntries {
			result.Truncated = true
			return errLimit
		}
		if entry.Type()&os.ModeSymlink != 0 {
			result.SkippedSymlinks++
			return nil
		}
		if entry.IsDir() {
			if rel != "." {
				depth := strings.Count(slashRel, "/") + 1
				if ignoredDirectory(entry.Name()) || depth > maxDepth {
					return filepath.SkipDir
				}
			}
			return nil
		}
		if !entry.Type().IsRegular() || !projectMarker(entry.Name()) {
			return nil
		}
		parent := filepath.ToSlash(filepath.Dir(rel))
		if markers[parent] == nil {
			markers[parent] = map[string]bool{}
		}
		markers[parent][entry.Name()] = true
		return nil
	})
	if err != nil && !errors.Is(err, errLimit) {
		return Map{}, fmt.Errorf("walk workspace: %w", err)
	}
	dirs := make([]string, 0, len(markers))
	for dir := range markers {
		dirs = append(dirs, dir)
	}
	sort.Strings(dirs)
	if len(dirs) > maxProjects {
		dirs = dirs[:maxProjects]
		result.Truncated = true
	}
	for _, dir := range dirs {
		manifestNames := make([]string, 0, len(markers[dir]))
		for name := range markers[dir] {
			manifestNames = append(manifestNames, name)
		}
		sort.Strings(manifestNames)
		projectRoot := filepath.Join(abs, filepath.FromSlash(dir))
		diagnosis, err := doctor.Inspect(projectRoot)
		if err != nil {
			// A path may disappear during scanning; return evidence instead of silently dropping it.
			result.ScanErrors = append(result.ScanErrors, fmt.Sprintf("%s: %v", dir, err))
			continue
		}
		result.Projects = append(result.Projects, Project{Path: dir, Markers: manifestNames, Report: diagnosis})
	}
	return result, nil
}

func projectMarker(name string) bool {
	switch name {
	case "go.mod", "package.json", "pyproject.toml", "requirements.txt", "pytest.ini", "Cargo.toml":
		return true
	}
	return strings.HasSuffix(name, ".csproj") && len(name) > len(".csproj")
}

func ignoredDirectory(name string) bool {
	switch name {
	case ".git", ".hg", ".svn", "node_modules", "vendor", ".venv", "venv", "__pycache__", ".next", ".nuxt", ".turbo", "dist", "build", "target", "coverage", ".idea", ".cache", "bin", "obj":
		return true
	}
	return false
}
