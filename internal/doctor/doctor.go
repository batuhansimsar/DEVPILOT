// Package doctor inspects developer workspaces without executing their contents.
package doctor

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

type Finding struct {
	Level    string `json:"level"`
	Code     string `json:"code"`
	Message  string `json:"message"`
	Evidence string `json:"evidence,omitempty"`
	Remedy   string `json:"remedy,omitempty"`
}

type Project struct {
	Directory  string   `json:"directory"`
	Languages  []string `json:"languages"`
	Frameworks []string `json:"frameworks,omitempty"`
	Manifests  []string `json:"manifests"`
}

type TestCommand struct {
	ID            string   `json:"id"`
	Directory     string   `json:"directory"`
	Program       string   `json:"program"`
	Args          []string `json:"args"`
	Evidence      string   `json:"evidence"`
	RequiresTrust bool     `json:"requires_trust"`
}

type GitInfo struct {
	IsRepository bool   `json:"is_repository"`
	Branch       string `json:"branch,omitempty"`
	Head         string `json:"head,omitempty"`
}

type Report struct {
	Root     string        `json:"root"`
	Projects []Project     `json:"projects"`
	Tests    []TestCommand `json:"tests"`
	Git      GitInfo       `json:"git"`
	Findings []Finding     `json:"findings"`
}

var manifestNames = map[string]string{
	"go.mod": "Go", "package.json": "JavaScript/TypeScript", "Cargo.toml": "Rust",
	"pyproject.toml": "Python", "requirements.txt": "Python", "Pipfile": "Python",
	"pom.xml": "Java", "build.gradle": "Java/Kotlin", "build.gradle.kts": "Java/Kotlin",
}
var ignoreDirs = map[string]bool{
	".git": true, "node_modules": true, ".venv": true, "venv": true, "vendor": true,
	"dist": true, "build": true, "target": true, "bin": true, "obj": true,
	".next": true, "__pycache__": true, ".idea": true,
}

// Analyze performs bounded, read-only filesystem inspection. It never executes
// repository code, loads .env secrets, or follows symlinks within the workspace.
func Analyze(root string) (Report, error) {
	if root == "" {
		root = "."
	}
	absolute, err := filepath.Abs(root)
	if err != nil {
		return Report{}, err
	}
	absolute, err = filepath.EvalSymlinks(absolute)
	if err != nil {
		return Report{}, fmt.Errorf("resolve workspace: %w", err)
	}
	st, err := os.Stat(absolute)
	if err != nil {
		return Report{}, fmt.Errorf("inspect workspace: %w", err)
	}
	if !st.IsDir() {
		return Report{}, fmt.Errorf("workspace is not a directory: %s", absolute)
	}

	r := Report{Root: absolute, Projects: []Project{}, Tests: []TestCommand{}, Findings: []Finding{}, Git: readGit(absolute)}
	files := map[string][]string{}
	entries := 0
	err = filepath.WalkDir(absolute, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return fmt.Errorf("inspect %s: %w", path, walkErr)
		}
		if path == absolute {
			return nil
		}
		rel, err := filepath.Rel(absolute, path)
		if err != nil {
			return err
		}
		depth := strings.Count(rel, string(filepath.Separator))
		if d.Type()&os.ModeSymlink != 0 {
			return nil
		}
		if d.IsDir() {
			if ignoreDirs[d.Name()] || (strings.HasPrefix(d.Name(), ".") && d.Name() != ".github") || depth >= 2 {
				return filepath.SkipDir
			}
			return nil
		}
		entries++
		if entries > 10000 {
			return errors.New("workspace scan exceeded 10000 files; use --path to select a smaller directory")
		}
		if depth > 2 {
			return nil
		}
		name := d.Name()
		if isManifest(name) || name == ".env.example" || name == ".env.sample" || name == ".env" || isLock(name) || name == "pytest.ini" || name == "conftest.py" {
			dir := filepath.Dir(rel)
			if dir == "." {
				dir = "."
			}
			files[dir] = append(files[dir], name)
		}
		return nil
	})
	if err != nil {
		return Report{}, err
	}
	dirs := make([]string, 0, len(files))
	for d := range files {
		dirs = append(dirs, d)
	}
	sort.Strings(dirs)
	hasProject := false
	for _, dir := range dirs {
		names := files[dir]
		sort.Strings(names)
		set := map[string]bool{}
		for _, n := range names {
			set[n] = true
		}
		languages := map[string]bool{}
		frameworks := map[string]bool{}
		manifests := []string{}
		for _, n := range names {
			if !isManifest(n) {
				continue
			}
			hasProject = true
			language := manifestLanguage(n)
			languages[language] = true
			manifests = append(manifests, filepath.ToSlash(filepath.Join(dir, n)))
		}
		dirPath := filepath.Join(absolute, dir)
		if set["package.json"] {
			body, e := safeRead(dirPath, "package.json")
			if e != nil {
				r.add("warning", "MANIFEST_UNREADABLE", fmt.Sprintf("Cannot read package.json: %v", e), relative(dir, "package.json"), "Repair the manifest or reduce its size")
			} else {
				var pkg struct {
					Dependencies    map[string]json.RawMessage `json:"dependencies"`
					DevDependencies map[string]json.RawMessage `json:"devDependencies"`
					Scripts         map[string]string          `json:"scripts"`
				}
				if e := json.Unmarshal(body, &pkg); e != nil {
					r.add("warning", "INVALID_PACKAGE_JSON", fmt.Sprintf("Invalid package.json: %v", e), relative(dir, "package.json"), "Fix JSON syntax")
				} else {
					for _, f := range []string{"react", "next", "vue", "@angular/core", "svelte", "express", "fastify", "vite", "nuxt"} {
						if _, ok := pkg.Dependencies[f]; ok {
							frameworks[f] = true
						}
						if _, ok := pkg.DevDependencies[f]; ok {
							frameworks[f] = true
						}
					}
					if script := strings.TrimSpace(pkg.Scripts["test"]); script != "" && !strings.Contains(script, "no test specified") {
						manager := nodeManager(set)
						program := map[string]string{"npm": "npm", "pnpm": "pnpm", "yarn": "yarn", "bun": "bun"}[manager]
						args := []string{"test"}
						r.Tests = append(r.Tests, TestCommand{ID: commandID("node", dir), Directory: dir, Program: program, Args: args, Evidence: relative(dir, "package.json") + " scripts.test", RequiresTrust: true})
					}
				}
			}
			locks := []string{}
			for _, lock := range []string{"package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb"} {
				if set[lock] {
					locks = append(locks, lock)
				}
			}
			// npm-shrinkwrap and package-lock can coexist intentionally; treat as one manager.
			managers := map[string]bool{}
			for _, lock := range locks {
				switch lock {
				case "package-lock.json", "npm-shrinkwrap.json":
					managers["npm"] = true
				case "pnpm-lock.yaml":
					managers["pnpm"] = true
				case "yarn.lock":
					managers["yarn"] = true
				default:
					managers["bun"] = true
				}
			}
			if len(managers) > 1 {
				r.add("warning", "CONFLICTING_LOCKFILES", "Multiple Node package managers have lockfiles in the same project", dir, "Keep the lockfile for the intended package manager")
			}
			if len(managers) == 0 {
				r.add("info", "NODE_LOCKFILE_MISSING", "No Node package-manager lockfile detected", relative(dir, "package.json"), "Commit a lockfile for reproducible installs")
			}
			requireTool(&r, nodeManager(set), dir)
		}
		if set["go.mod"] {
			r.Tests = append(r.Tests, TestCommand{ID: commandID("go", dir), Directory: dir, Program: "go", Args: []string{"test", "./..."}, Evidence: relative(dir, "go.mod"), RequiresTrust: true})
			requireTool(&r, "go", dir)
		}
		if set["Cargo.toml"] {
			r.Tests = append(r.Tests, TestCommand{ID: commandID("cargo", dir), Directory: dir, Program: "cargo", Args: []string{"test"}, Evidence: relative(dir, "Cargo.toml"), RequiresTrust: true})
			requireTool(&r, "cargo", dir)
		}
		if set["pytest.ini"] || set["conftest.py"] {
			r.Tests = append(r.Tests, TestCommand{ID: commandID("pytest", dir), Directory: dir, Program: "python3", Args: []string{"-m", "pytest"}, Evidence: dir, RequiresTrust: true})
			requireTool(&r, "python3", dir)
		}
		if set["pom.xml"] {
			r.Tests = append(r.Tests, TestCommand{ID: commandID("maven", dir), Directory: dir, Program: "mvn", Args: []string{"test"}, Evidence: relative(dir, "pom.xml"), RequiresTrust: true})
			requireTool(&r, "mvn", dir)
		}
		if set["build.gradle"] || set["build.gradle.kts"] {
			r.Tests = append(r.Tests, TestCommand{ID: commandID("gradle", dir), Directory: dir, Program: "gradle", Args: []string{"test"}, Evidence: dir, RequiresTrust: true})
			requireTool(&r, "gradle", dir)
		}
		for _, n := range names {
			if strings.HasSuffix(strings.ToLower(n), ".csproj") && (strings.Contains(strings.ToLower(n), "test") || isTestProject(dirPath, n)) {
				r.Tests = append(r.Tests, TestCommand{ID: commandID("dotnet", dir+"/"+n), Directory: dir, Program: "dotnet", Args: []string{"test", n}, Evidence: relative(dir, n), RequiresTrust: true})
				requireTool(&r, "dotnet", dir)
			}
		}
		for _, n := range []string{".env.example", ".env.sample"} {
			if set[n] && !set[".env"] {
				r.add("info", "ENV_TEMPLATE_FOUND", "Environment template exists, but no .env file was found (variables may be supplied another way)", relative(dir, n), "Review the template and configure only the variables this project needs")
			}
		}
		if len(manifests) > 0 {
			r.Projects = append(r.Projects, Project{Directory: dir, Languages: sortedKeys(languages), Frameworks: sortedKeys(frameworks), Manifests: manifests})
		}
	}
	if !hasProject {
		r.add("warning", "NO_PROJECT_MANIFEST", "No recognized project manifest found within scan depth", ".", "Run from the project root or use --path to inspect a subproject")
	}
	if len(r.Tests) == 0 {
		r.add("info", "NO_TEST_COMMAND", "No supported test entry point detected", ".", "Add a test target to a supported manifest")
	}
	if !r.Git.IsRepository {
		r.add("info", "NO_GIT_REPOSITORY", "No Git metadata detected at the selected root", ".git", "Initialize Git if version control is needed")
	}
	sort.Slice(r.Tests, func(i, j int) bool { return r.Tests[i].ID < r.Tests[j].ID })
	sort.Slice(r.Findings, func(i, j int) bool {
		if r.Findings[i].Code == r.Findings[j].Code {
			return r.Findings[i].Evidence < r.Findings[j].Evidence
		}
		return r.Findings[i].Code < r.Findings[j].Code
	})
	return r, nil
}

func (r *Report) add(level, code, msg, evidence, remedy string) {
	r.Findings = append(r.Findings, Finding{level, code, msg, evidence, remedy})
}
func sortedKeys(m map[string]bool) []string {
	out := []string{}
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
func relative(dir, name string) string  { return filepath.ToSlash(filepath.Join(dir, name)) }
func commandID(kind, dir string) string { return kind + ":" + filepath.ToSlash(dir) }
func manifestLanguage(n string) string {
	if strings.HasSuffix(strings.ToLower(n), ".csproj") || strings.HasSuffix(strings.ToLower(n), ".sln") || strings.HasSuffix(strings.ToLower(n), ".slnx") {
		return "C#/.NET"
	}
	return manifestNames[n]
}
func isManifest(n string) bool {
	if _, ok := manifestNames[n]; ok {
		return true
	}
	low := strings.ToLower(n)
	return strings.HasSuffix(low, ".csproj") || strings.HasSuffix(low, ".sln") || strings.HasSuffix(low, ".slnx")
}
func isLock(n string) bool {
	switch n {
	case "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb":
		return true
	}
	return false
}
func nodeManager(s map[string]bool) string {
	if s["pnpm-lock.yaml"] {
		return "pnpm"
	}
	if s["yarn.lock"] {
		return "yarn"
	}
	if s["bun.lock"] || s["bun.lockb"] {
		return "bun"
	}
	return "npm"
}
func requireTool(r *Report, name, dir string) {
	if _, err := exec.LookPath(name); err != nil {
		for _, f := range r.Findings {
			if f.Code == "TOOL_MISSING" && f.Evidence == name {
				return
			}
		}
		r.add("warning", "TOOL_MISSING", fmt.Sprintf("%s is not available on PATH (needed by %s)", name, dir), name, "Install the tool or configure PATH")
	}
}
func safeRead(dir, name string) ([]byte, error) {
	path := filepath.Join(dir, name)
	info, e := os.Lstat(path)
	if e != nil {
		return nil, e
	}
	if !info.Mode().IsRegular() {
		return nil, errors.New("not a regular file")
	}
	if info.Size() > 1<<20 {
		return nil, errors.New("file exceeds 1 MiB scan limit")
	}
	return os.ReadFile(path)
}
func isTestProject(dir, name string) bool {
	b, e := safeRead(dir, name)
	if e != nil {
		return false
	}
	s := strings.ToLower(string(b))
	return strings.Contains(s, "<istestproject>true</istestproject>") || strings.Contains(s, "microsoft.net.test.sdk")
}

var refName = regexp.MustCompile(`^refs/heads/[a-zA-Z0-9_./-]+$`)

func readGit(root string) GitInfo {
	path := filepath.Join(root, ".git")
	info, err := os.Lstat(path)
	if err != nil || (!info.IsDir() && !info.Mode().IsRegular()) {
		return GitInfo{}
	}
	gitDir := path
	if info.Mode().IsRegular() {
		b, e := safeRead(root, ".git")
		if e != nil {
			return GitInfo{}
		}
		v := strings.TrimSpace(string(b))
		if !strings.HasPrefix(v, "gitdir: ") {
			return GitInfo{}
		}
		candidate := strings.TrimSpace(strings.TrimPrefix(v, "gitdir: "))
		if filepath.IsAbs(candidate) {
			gitDir = candidate
		} else {
			gitDir = filepath.Join(root, candidate)
		}
		// Worktrees may contain a .git pointer outside the workspace; don't follow it.
		abs, e := filepath.Abs(gitDir)
		if e != nil || !within(root, abs) {
			return GitInfo{IsRepository: true}
		}
		gitDir = abs
	}
	head, e := safeRead(gitDir, "HEAD")
	if e != nil {
		return GitInfo{IsRepository: true}
	}
	v := strings.TrimSpace(string(head))
	result := GitInfo{IsRepository: true}
	if strings.HasPrefix(v, "ref: ") {
		ref := strings.TrimPrefix(v, "ref: ")
		if refName.MatchString(ref) {
			result.Branch = strings.TrimPrefix(ref, "refs/heads/")
		}
	}
	if len(v) == 40 && isHex(v) {
		result.Head = v
	}
	return result
}
func within(root, target string) bool {
	rel, err := filepath.Rel(root, target)
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}
func isHex(s string) bool {
	for _, ch := range s {
		if !strings.ContainsRune("0123456789abcdefABCDEF", ch) {
			return false
		}
	}
	return true
}
