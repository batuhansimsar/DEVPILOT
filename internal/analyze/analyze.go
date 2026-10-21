// Package analyze provides bounded, read-only repository inventory.
// It never follows symbolic links or executes project-controlled commands.
package analyze

import (
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// MaxFiles prevents pathological or malicious workspaces from causing unbounded scans.
const MaxFiles = 20000

var ignored = map[string]bool{
	".git": true, ".hg": true, ".svn": true, ".venv": true,
	"venv": true, "node_modules": true, "vendor": true, ".next": true,
	"dist": true, "build": true, "target": true, "coverage": true,
	".gradle": true, ".terraform": true, "__pycache__": true,
	".pytest_cache": true, "bin": true, "obj": true,
}

var languages = map[string]string{
	".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
	".mjs": "JavaScript", ".cjs": "JavaScript",
	".ts": "TypeScript", ".tsx": "TypeScript",
	".mts": "TypeScript", ".cts": "TypeScript", ".cs": "C#",
	".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
	".cpp": "C++", ".cc": "C++", ".c": "C", ".rb": "Ruby",
	".php": "PHP", ".swift": "Swift", ".dart": "Dart",
	".sh": "Shell", ".sql": "SQL", ".vue": "Vue",
	".svelte": "Svelte", ".html": "HTML", ".css": "CSS",
	".tf": "Terraform",
}

var markers = map[string]string{
	"go.mod": "Go", "go.work": "Go", "Cargo.toml": "Rust", "package.json": "Node.js",
	"pyproject.toml": "Python", "requirements.txt": "Python", "Pipfile.lock": "Python",
	"Pipfile": "Python", "uv.lock": "Python", "poetry.lock": "Python", "pdm.lock": "Python",
	"pom.xml": "Maven", "build.gradle": "Gradle",
	"build.gradle.kts": "Gradle", "Gemfile": "Ruby",
	"composer.json": "PHP", "pubspec.yaml": "Dart",
	"deno.json": "Deno", "deno.jsonc": "Deno", "bun.lock": "Bun", "bun.lockb": "Bun",
}

// LanguageCount is one language and its file count.
type LanguageCount struct {
	Name  string `json:"name"`
	Files int    `json:"files"`
}

// Report contains only relative file paths and counts, never source contents.
type Report struct {
	Path      string          `json:"path"`
	FileCount int             `json:"file_count"`
	Truncated bool            `json:"truncated"`
	Languages []LanguageCount `json:"languages"`
	Manifests []string        `json:"manifests"`
	CI        []string        `json:"ci"`
	Containers []string       `json:"containers"`
	Warnings  []string        `json:"warnings"`
}

// Inspect walks the project without following symlinked dirs or files.
// It deliberately skips generated/dependency trees and bounds the scan.
func Inspect(path string) (Report, error) {
	root, err := projectRoot(path)
	if err != nil {
		return Report{}, err
	}

	r := Report{Path: root, Languages: []LanguageCount{}, Manifests: []string{}, CI: []string{}, Containers: []string{}, Warnings: []string{}}
	counts := map[string]int{}
	err = filepath.WalkDir(root, func(current string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			// Permission errors are reported, not silently mistaken for a complete scan.
			relative, _ := filepath.Rel(root, current)
			r.Warnings = append(r.Warnings, "Cannot inspect "+filepath.ToSlash(relative)+": "+walkErr.Error())
			return nil
		}
		if current == root {
			return nil
		}
		if entry.Type()&os.ModeSymlink != 0 {
			return nil
		}
		if entry.IsDir() {
			if ignored[entry.Name()] {
				return filepath.SkipDir
			}
			return nil
		}
		if !entry.Type().IsRegular() {
			return nil
		}
		if r.FileCount >= MaxFiles {
			r.Truncated = true
			return filepath.SkipAll
		}
		r.FileCount++
		relative, err := filepath.Rel(root, current)
		if err != nil {
			return err
		}
		relative = filepath.ToSlash(relative)
		if lang, ok := languages[strings.ToLower(filepath.Ext(entry.Name()))]; ok {
			counts[lang]++
		}
		if eco, ok := markers[entry.Name()]; ok {
			r.Manifests = append(r.Manifests, relative+" ("+eco+")")
		} else if isDotnetManifest(entry.Name()) {
			r.Manifests = append(r.Manifests, relative+" (.NET)")
		} else if kind, ok := dockerManifestKind(entry.Name()); ok {
			r.Manifests = append(r.Manifests, relative+" ("+kind+")")
		}
		if isCIConfig(relative) {
			r.CI = append(r.CI, relative)
		}
		if isContainerConfig(entry.Name()) {
			r.Containers = append(r.Containers, relative)
		}
		return nil
	})
	if err != nil && !errors.Is(err, filepath.SkipAll) {
		return Report{}, err
	}
	for name, files := range counts {
		r.Languages = append(r.Languages, LanguageCount{Name: name, Files: files})
	}
	sort.Slice(r.Languages, func(i, j int) bool {
		if r.Languages[i].Files == r.Languages[j].Files {
			return r.Languages[i].Name < r.Languages[j].Name
		}
		return r.Languages[i].Files > r.Languages[j].Files
	})
	sort.Strings(r.Manifests)
	sort.Strings(r.CI)
	sort.Strings(r.Containers)
	sort.Strings(r.Warnings)
	return r, nil
}

// isDotnetManifest detects .NET project and solution files without opening them.
// Extension matching is case-insensitive and includes modern .slnx files.
func isDotnetManifest(name string) bool {
	switch strings.ToLower(filepath.Ext(name)) {
	case ".csproj", ".fsproj", ".vbproj", ".sln", ".slnx":
		return true
	default:
		return false
	}
}
