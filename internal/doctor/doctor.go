// Package doctor performs a conservative, read-only inspection of a project root.
// It does not execute repository scripts or read environment variable values.
package doctor

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// Finding describes a verifiable observation and, when useful, a next action.
type Finding struct {
	Level   string `json:"level"`
	Code    string `json:"code"`
	Message string `json:"message"`
	Remedy  string `json:"remedy,omitempty"`
}

type TestCommand struct {
	Executable string   `json:"executable"`
	Arguments  []string `json:"arguments"`
}

type Report struct {
	Path           string       `json:"path"`
	Languages      []string     `json:"languages"`
	Frameworks     []string     `json:"frameworks"`
	PackageManager string       `json:"package_manager,omitempty"`
	Tests          *TestCommand `json:"tests,omitempty"`
	Findings       []Finding    `json:"findings"`
}

func (r Report) HasWarnings() bool {
	for _, f := range r.Findings {
		if f.Level == "warning" {
			return true
		}
	}
	return false
}

var variableName = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)

// readMarker refuses symbolic links and oversized files. A malicious project must
// not be able to trick project detection into reading files outside the root.
func readMarker(root, name string) ([]byte, bool, error) {
	path := filepath.Join(root, name)
	st, err := os.Lstat(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil, false, nil
	}
	if err != nil {
		return nil, false, err
	}
	if !st.Mode().IsRegular() {
		return nil, false, fmt.Errorf("%s is not a regular file", name)
	}
	if st.Size() > 1024*1024 {
		return nil, false, fmt.Errorf("%s exceeds 1 MiB inspection limit", name)
	}
	return readMarkerAfterStat(path, name, st)
}

// readMarkerAfterStat verifies the opened file is exactly the regular file
// observed by Lstat. A workspace can swap a path between Lstat and Open;
// no contents are read until the open descriptor has been validated.
func readMarkerAfterStat(path, name string, expected os.FileInfo) ([]byte, bool, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, false, err
	}
	defer f.Close()
	opened, err := f.Stat()
	if err != nil {
		return nil, false, err
	}
	if !opened.Mode().IsRegular() || !os.SameFile(expected, opened) {
		return nil, false, fmt.Errorf("%s changed while opening for inspection", name)
	}
	if opened.Size() > 1024*1024 {
		return nil, false, fmt.Errorf("%s exceeds 1 MiB inspection limit", name)
	}
	b, err := io.ReadAll(io.LimitReader(f, 1024*1024+1))
	if err != nil {
		return nil, false, err
	}
	if len(b) > 1024*1024 {
		return nil, false, fmt.Errorf("%s exceeds 1 MiB inspection limit", name)
	}
	return b, true, nil
}

func hasMarker(root, name string) bool {
	st, err := os.Lstat(filepath.Join(root, name))
	return err == nil && st.Mode().IsRegular()
}

func namesFromEnv(data []byte) []string {
	set := make(map[string]bool)
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(line), "\ufeff"))
		if strings.HasPrefix(line, "export") && len(line) > len("export") &&
			(line[len("export")] == ' ' || line[len("export")] == '\t') {
			line = strings.TrimSpace(line[len("export"):])
		}
		name, _, ok := strings.Cut(line, "=")
		if ok && variableName.MatchString(strings.TrimSpace(name)) {
			set[strings.TrimSpace(name)] = true
		}
	}
	names := make([]string, 0, len(set))
	for n := range set {
		names = append(names, n)
	}
	sort.Strings(names)
	return names
}

func Inspect(root string) (Report, error) {
	abs, err := filepath.Abs(root)
	if err != nil {
		return Report{}, err
	}
	st, err := os.Stat(abs)
	if err != nil {
		return Report{}, fmt.Errorf("project directory: %w", err)
	}
	if !st.IsDir() {
		return Report{}, fmt.Errorf("project path is not a directory: %s", abs)
	}

	r := Report{Path: abs, Languages: []string{}, Frameworks: []string{}, Findings: []Finding{}}
	add := func(level, code, message, remedy string) {
		r.Findings = append(r.Findings, Finding{Level: level, Code: code, Message: message, Remedy: remedy})
	}
	language := func(name string) {
		for _, v := range r.Languages {
			if v == name {
				return
			}
		}
		r.Languages = append(r.Languages, name)
	}
	framework := func(name string) {
		for _, v := range r.Frameworks {
			if v == name {
				return
			}
		}
		r.Frameworks = append(r.Frameworks, name)
	}
	tool := func(name, description string) {
		if _, err := exec.LookPath(name); err != nil {
			add("warning", "missing-tool-"+name, description+" is not on PATH", "Install "+name+" and ensure it is on PATH.")
		} else {
			add("pass", "tool-"+name, description+" is available", "")
		}
	}

	if hasMarker(abs, "go.mod") {
		language("Go")
		r.Tests = &TestCommand{Executable: "go", Arguments: []string{"test", "./..."}}
		tool("go", "Go toolchain")
	}
	if hasMarker(abs, "Cargo.toml") {
		language("Rust")
		if r.Tests == nil {
			r.Tests = &TestCommand{Executable: "cargo", Arguments: []string{"test"}}
		}
		tool("cargo", "Cargo")
	}
	if hasMarker(abs, "requirements.txt") || hasMarker(abs, "pyproject.toml") || hasMarker(abs, "pytest.ini") {
		language("Python")
		if hasMarker(abs, "pytest.ini") || hasMarker(abs, "pyproject.toml") {
			if r.Tests == nil {
				r.Tests = &TestCommand{Executable: "python", Arguments: []string{"-m", "pytest"}}
			}
		}
		tool("python", "Python")
	}
	if hasMarker(abs, "package.json") {
		language("JavaScript/TypeScript")
		data, _, err := readMarker(abs, "package.json")
		if err != nil {
			add("warning", "package-json-unreadable", "Cannot inspect package.json: "+err.Error(), "Make package.json a regular file smaller than 1 MiB.")
		} else {
			var pkg struct {
				PackageManager  string                     `json:"packageManager"`
				Scripts         map[string]string          `json:"scripts"`
				Dependencies    map[string]json.RawMessage `json:"dependencies"`
				DevDependencies map[string]json.RawMessage `json:"devDependencies"`
			}
			if err := json.Unmarshal(data, &pkg); err != nil {
				add("warning", "package-json-invalid", "package.json is invalid JSON", "Fix JSON syntax before installing dependencies.")
			} else {
				deps := make(map[string]bool)
				for k := range pkg.Dependencies {
					deps[k] = true
				}
				for k := range pkg.DevDependencies {
					deps[k] = true
				}
				for dep, name := range map[string]string{"react": "React", "next": "Next.js", "vue": "Vue", "@angular/core": "Angular", "express": "Express", "vite": "Vite"} {
					if deps[dep] {
						framework(name)
					}
				}
				manager, executable, lockfiles := detectJSLockfiles(abs)
				if declared := declaredNodeManager(pkg.PackageManager); declared != "" {
					if len(lockfiles) == 0 {
						manager, executable = declared, declared
					} else if declared != manager {
						add("warning", "js-package-manager-mismatch", "packageManager specifies "+declared+" but the lockfile selects "+manager, "Align packageManager and the committed lockfile before installing dependencies.")
					}
				}
				// A packageManager declaration must never choose arbitrary executables.
				// Keep lockfile precedence for existing workspaces but report invalid
				// declarations and conflicts between multiple lockfile families.
				_, metadataFindings := selectNodePackageManager(pkg.PackageManager, manager, lockfiles)
				for _, issue := range metadataFindings {
					if issue.Code == "package-manager-invalid" || (issue.Code == "package-manager-lock-mismatch" && len(lockfiles) > 1) {
						add(issue.Level, issue.Code, issue.Message, issue.Remedy)
					}
				}
				r.PackageManager = manager
				if len(lockfiles) > 1 {
					add("warning", "js-lockfiles-conflict", "Multiple JavaScript lockfiles detected: "+strings.Join(lockfiles, ", "), "Keep only the lockfile for the selected package manager after confirming which one is authoritative.")
				}
				if _, exists := pkg.Scripts["test"]; exists && r.Tests == nil {
					// Package scripts can execute arbitrary code. Execution requires explicit --trust.
					r.Tests = &TestCommand{Executable: executable, Arguments: nodeTestArgs(executable)}
				}
				tool(executable, manager+" package manager")
			}
		}
	}
	dotnet, err := discoverDotnet(abs)
	if err != nil {
		add("warning", "dotnet-discovery-failed", "Cannot inspect .NET project entries: "+err.Error(), "Check directory access.")
	} else if dotnet.Found {
		for _, name := range dotnet.Languages {
			language(name)
		}
		framework(".NET")
		tool("dotnet", ".NET SDK")
		if r.Tests == nil && dotnet.TestTarget != "" {
			r.Tests = &TestCommand{Executable: "dotnet", Arguments: []string{"test", dotnet.TestTarget}}
		}
		if dotnet.Ambiguous {
			add("info", "dotnet-ambiguous-target", "Multiple .NET project or solution files found; cannot choose a test target safely", "Run dotnet test with an explicit project or solution path.")
		}
	}
	if len(r.Languages) == 0 && len(r.Frameworks) == 0 {
		add("info", "unknown-project", "No supported project manifest was found at the project root", "Open the directory containing a go.mod, package.json, Cargo.toml or similar manifest.")
	}
	if r.Tests == nil {
		add("info", "no-test-command", "No supported test command was discovered", "Add a project test configuration if tests exist.")
	} else {
		add("pass", "test-discovered", "Detected test command: "+r.Tests.Executable+" "+strings.Join(r.Tests.Arguments, " "), "Execute only in a trusted workspace: devpilot test --trust")
	}

	for _, example := range []string{".env.example", ".env.sample", ".env.template"} {
		data, found, err := readMarker(abs, example)
		if err != nil {
			add("warning", "env-example-unreadable", "Cannot inspect "+example+": "+err.Error(), "Review file type and size.")
			continue
		}
		if !found {
			continue
		}
		expected := namesFromEnv(data)
		if len(expected) == 0 {
			continue
		}
		actualData, present, err := readMarker(abs, ".env")
		if err != nil {
			add("info", "env-local-unreadable", "Local .env cannot be inspected", "Check environment variable names manually; values are never read by DevPilot.")
			break
		}
		if !present {
			add("info", "env-local-absent", fmt.Sprintf("%s documents %d variable names; no local .env file found (variables may be supplied externally)", example, len(expected)), "Review the example and configure required variables in your environment.")
			break
		}
		set := make(map[string]bool)
		for _, name := range namesFromEnv(actualData) {
			set[name] = true
		}
		missing := []string{}
		for _, name := range expected {
			if !set[name] {
				missing = append(missing, name)
			}
		}
		if len(missing) > 0 {
			add("info", "env-local-missing-keys", fmt.Sprintf("%d example keys are not declared in .env: %s (they may be provided externally)", len(missing), strings.Join(missing, ", ")), "Review local or externally supplied environment variables.")
		} else {
			add("pass", "env-local-keys", ".env contains all variable names from "+example+" (values not checked)", "")
		}
		break
	}

	// Read .git/HEAD instead of invoking git: git status can execute repository-
	// configured filters and file-system monitors in an untrusted workspace.
	if st, err := os.Lstat(filepath.Join(abs, ".git")); err == nil && st.IsDir() {
		head, found, err := readMarker(abs, filepath.Join(".git", "HEAD"))
		if err != nil {
			add("info", "git-head-unreadable", "Cannot inspect Git HEAD", "Inspect Git metadata manually.")
		} else if found {
			if branch, ok := parseGitHeadBranch(head); ok {
				add("info", "git-branch", "Git branch: "+branch+" (working-tree status not inspected)", "Run git status yourself in a trusted workspace.")
			} else if isGitDetachedHead(head) {
				add("info", "git-detached", "Git HEAD is detached", "Run git status in a trusted workspace.")
			}
		}
	}
	sort.Strings(r.Languages)
	sort.Strings(r.Frameworks)
	return r, nil
}
