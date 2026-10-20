// Package doctor performs read-only, evidence-based project inspection.
package doctor

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

type Finding struct {
	Severity string `json:"severity"`
	Code     string `json:"code"`
	Evidence string `json:"evidence"`
	Remedy   string `json:"remedy"`
}

type TestCommand struct {
	Tool   string   `json:"tool"`
	Args   []string `json:"args"`
	Source string   `json:"source"`
}

type Report struct {
	Root            string        `json:"root"`
	Languages       []string      `json:"languages"`
	Frameworks      []string      `json:"frameworks"`
	PackageManagers []string      `json:"package_managers"`
	TestCommands    []TestCommand `json:"test_commands"`
	Git             bool          `json:"git"`
	DockerCompose   bool          `json:"docker_compose"`
	Findings        []Finding     `json:"findings"`
}

var envKey = regexp.MustCompile(`(?m)^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=`)

// Inspect never executes project code, reads secret values, or traverses subdirectories.
// It only examines known, regular, top-level manifest files.
func Inspect(path string) (Report, error) {
	root, err := filepath.Abs(path)
	if err != nil {
		return Report{}, err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return Report{}, fmt.Errorf("resolve workspace: %w", err)
	}
	stat, err := os.Stat(root)
	if err != nil {
		return Report{}, fmt.Errorf("open workspace: %w", err)
	}
	if !stat.IsDir() {
		return Report{}, fmt.Errorf("workspace is not a directory: %s", root)
	}
	r := Report{Root: root, Languages: []string{}, Frameworks: []string{}, PackageManagers: []string{}, TestCommands: []TestCommand{}, Findings: []Finding{}}
	add := func(severity, code, evidence, remedy string) {
		r.Findings = append(r.Findings, Finding{severity, code, evidence, remedy})
	}
	has := func(name string) bool {
		info, e := os.Lstat(filepath.Join(root, name))
		return e == nil && info.Mode().IsRegular()
	}
	read := func(name string) ([]byte, error) {
		if !has(name) {
			return nil, os.ErrNotExist
		}
		return os.ReadFile(filepath.Join(root, name))
	}
	r.Git = existsGit(root)
	if !r.Git {
		add("info", "git-not-found", "No .git directory or worktree file at the workspace root.", "Initialize Git if version control is intended.")
	}
	for _, name := range []string{"compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"} {
		if has(name) {
			r.DockerCompose = true
			break
		}
	}
	if r.DockerCompose {
		add("info", "compose-found", "Docker Compose configuration present.", "Use docker compose config to validate it in a trusted workspace.")
	}
	if has("go.mod") {
		r.Languages = append(r.Languages, "Go")
		r.TestCommands = append(r.TestCommands, TestCommand{"go", []string{"test", "./..."}, "go.mod"})
		checkTool("go", "Go", &r)
	}
	if has("Cargo.toml") {
		r.Languages = append(r.Languages, "Rust")
		r.PackageManagers = append(r.PackageManagers, "cargo")
		r.TestCommands = append(r.TestCommands, TestCommand{"cargo", []string{"test"}, "Cargo.toml"})
		checkTool("cargo", "Rust", &r)
	}
	if has("pyproject.toml") || has("requirements.txt") || has("pytest.ini") {
		r.Languages = append(r.Languages, "Python")
		checkTool("python", "Python", &r)
		if has("pytest.ini") || has("conftest.py") {
			r.TestCommands = append(r.TestCommands, TestCommand{"python", []string{"-m", "pytest"}, "pytest configuration"})
		} else if data, e := read("pyproject.toml"); e == nil && strings.Contains(string(data), "pytest") {
			r.TestCommands = append(r.TestCommands, TestCommand{"python", []string{"-m", "pytest"}, "pyproject.toml"})
		}
	}
	if has("pom.xml") {
		r.Languages = append(r.Languages, "Java")
		r.PackageManagers = append(r.PackageManagers, "maven")
		r.TestCommands = append(r.TestCommands, TestCommand{"mvn", []string{"test"}, "pom.xml"})
		checkTool("mvn", "Maven", &r)
	}
	if has("build.gradle") || has("build.gradle.kts") {
		r.Languages = append(r.Languages, "Java/Kotlin")
		r.PackageManagers = append(r.PackageManagers, "gradle")
		add("info", "gradle-tests", "Gradle build detected; test task availability has not been verified.", "Inspect Gradle tasks before running tests.")
	}
	entries, err := os.ReadDir(root)
	if err != nil {
		return Report{}, fmt.Errorf("list workspace: %w", err)
	}
	for _, e := range entries {
		if !e.Type().IsRegular() {
			continue
		}
		if strings.HasSuffix(e.Name(), ".csproj") || strings.HasSuffix(e.Name(), ".sln") {
			r.Languages = append(r.Languages, "C#")
			checkTool("dotnet", ".NET", &r)
			r.TestCommands = append(r.TestCommands, TestCommand{"dotnet", []string{"test"}, e.Name()})
			break
		}
	}
	if has("package.json") {
		data, e := read("package.json")
		if e != nil {
			add("error", "package-read-failed", "Cannot read package.json: "+e.Error(), "Check file permissions.")
		} else {
			var pkg struct {
				PackageManager  string                     `json:"packageManager"`
				Scripts         map[string]string          `json:"scripts"`
				Dependencies    map[string]json.RawMessage `json:"dependencies"`
				DevDependencies map[string]json.RawMessage `json:"devDependencies"`
			}
			if err := json.Unmarshal(data, &pkg); err != nil {
				add("error", "package-json-invalid", "package.json is invalid JSON: "+err.Error(), "Fix the JSON syntax.")
			} else {
				r.Languages = append(r.Languages, "JavaScript/TypeScript")
				for _, f := range []struct{ name, label string }{{"react", "React"}, {"next", "Next.js"}, {"vue", "Vue"}, {"@angular/core", "Angular"}, {"vite", "Vite"}, {"express", "Express"}, {"typescript", "TypeScript"}} {
					if _, ok := pkg.Dependencies[f.name]; ok {
						r.Frameworks = append(r.Frameworks, f.label)
					} else if _, ok := pkg.DevDependencies[f.name]; ok {
						r.Frameworks = append(r.Frameworks, f.label)
					}
				}
				locks := []string{}
				for _, lock := range []string{"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb"} {
					if has(lock) {
						locks = append(locks, lock)
					}
				}
				if len(locks) > 1 {
					add("warning", "multiple-lockfiles", "Multiple package locks: "+strings.Join(locks, ", "), "Keep the lockfile used by your project's chosen package manager.")
				}
				manager := "npm"
				if pkg.PackageManager != "" {
					manager = strings.SplitN(pkg.PackageManager, "@", 2)[0]
				} else if len(locks) == 1 {
					switch locks[0] {
					case "pnpm-lock.yaml":
						manager = "pnpm"
					case "yarn.lock":
						manager = "yarn"
					case "bun.lock", "bun.lockb":
						manager = "bun"
					}
				}
				if manager != "npm" && manager != "pnpm" && manager != "yarn" && manager != "bun" {
					add("warning", "unknown-package-manager", "Unknown packageManager field: "+pkg.PackageManager, "Check packageManager in package.json.")
				} else {
					r.PackageManagers = append(r.PackageManagers, manager)
					checkTool(manager, "JavaScript package manager", &r)
					checkTool("node", "Node.js runtime", &r)
					if _, ok := pkg.Scripts["test"]; ok {
						r.TestCommands = append(r.TestCommands, TestCommand{manager, []string{"test"}, "package.json scripts.test"})
					} else {
						add("info", "no-node-test-script", "package.json has no scripts.test entry.", "Add a test script if the project has automated tests.")
					}
				}
				if !has("node_modules") { // node_modules is normally a directory, so inspect it separately below.
					if info, err := os.Lstat(filepath.Join(root, "node_modules")); err != nil || !info.IsDir() {
						add("info", "node-modules-absent", "No node_modules directory at the workspace root.", "Install dependencies with the project's chosen package manager if needed.")
					}
				}
			}
		}
	}
	if has(".env.example") {
		data, e := read(".env.example")
		if e == nil {
			names := map[string]bool{}
			for _, match := range envKey.FindAllSubmatch(data, -1) {
				names[string(match[1])] = true
			}
			if len(names) > 0 {
				add("info", "env-template", ".env.example declares "+fmt.Sprint(len(names))+" variable name(s); values were not read.", "Consult .env.example and provide values through your preferred secret-management method.")
			}
		}
	}
	if len(r.Languages) == 0 {
		add("info", "unknown-project", "No supported top-level project manifest was found.", "Run from the application root, or contribute a detector for this ecosystem.")
	}
	r.Languages = unique(r.Languages)
	r.Frameworks = unique(r.Frameworks)
	r.PackageManagers = unique(r.PackageManagers)
	return r, nil
}

func checkTool(name, label string, r *Report) {
	if _, err := exec.LookPath(name); err != nil {
		r.Findings = append(r.Findings, Finding{"warning", "tool-unavailable", label + " tool not found in PATH: " + name, "Install the tool or make it available in PATH."})
	}
}

func existsGit(root string) bool {
	info, err := os.Lstat(filepath.Join(root, ".git"))
	return err == nil && (info.IsDir() || info.Mode().IsRegular())
}

func unique(in []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(in))
	for _, item := range in {
		if !seen[item] {
			out = append(out, item)
			seen[item] = true
		}
	}
	sort.Strings(out)
	return out
}
