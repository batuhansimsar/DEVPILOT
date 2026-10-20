// Package doctor performs evidence-based, read-only repository diagnostics.
package doctor

import (
	"context"
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
	"sync"
	"time"
)

// Severity values are stable so tools can consume the JSON report.
type Severity string

const (
	Info    Severity = "info"
	Warning Severity = "warning"
	Error   Severity = "error"
)

type Finding struct {
	Severity Severity `json:"severity"`
	Code     string   `json:"code"`
	Message  string   `json:"message"`
	Evidence []string `json:"evidence,omitempty"`
	Remedy   string   `json:"remedy,omitempty"`
}

type Detection struct {
	Name     string   `json:"name"`
	Kind     string   `json:"kind"`
	Evidence []string `json:"evidence"`
}

type TestCommand struct {
	Directory  string   `json:"directory"`
	Executable string   `json:"executable"`
	Arguments  []string `json:"arguments"`
}

type TestResult struct {
	Command  TestCommand `json:"command"`
	Passed   bool        `json:"passed"`
	TimedOut bool        `json:"timed_out,omitempty"`
	Output   string      `json:"output,omitempty"`
}

type Report struct {
	SchemaVersion int           `json:"schema_version"`
	Workspace     string        `json:"workspace"`
	Detections    []Detection   `json:"detections"`
	Findings      []Finding     `json:"findings"`
	TestCommands  []TestCommand `json:"test_commands"`
	TestResults   []TestResult  `json:"test_results,omitempty"`
}

type Options struct {
	RunTests       bool
	TrustWorkspace bool
	Timeout        time.Duration
}

const maxManifestBytes = 1 << 20 // Never parse arbitrarily large or hostile manifests.
const maxTestOutputBytes = 12 << 10

func (r *Report) add(level Severity, code, message, remedy string, evidence ...string) {
	r.Findings = append(r.Findings, Finding{Severity: level, Code: code, Message: message, Remedy: remedy, Evidence: evidence})
}

// Analyze reads project metadata. It never runs application code unless both
// RunTests and TrustWorkspace are explicitly set. Repository data is untrusted.
func Analyze(ctx context.Context, root string, opts Options) (Report, error) {
	var report Report
	absolute, err := filepath.Abs(root)
	if err != nil {
		return report, fmt.Errorf("resolve workspace: %w", err)
	}
	rootInfo, err := os.Stat(absolute)
	if err != nil {
		return report, fmt.Errorf("open workspace: %w", err)
	}
	if !rootInfo.IsDir() {
		return report, fmt.Errorf("workspace is not a directory: %s", absolute)
	}
	if opts.RunTests && !opts.TrustWorkspace {
		return report, errors.New("--run-tests requires --trust-workspace; tests execute code from the repository")
	}
	if opts.Timeout <= 0 {
		opts.Timeout = 2 * time.Minute
	}
	report = Report{SchemaVersion: 1, Workspace: absolute, Detections: []Detection{}, Findings: []Finding{}, TestCommands: []TestCommand{}}

	manifests, err := discover(absolute)
	if err != nil {
		return report, fmt.Errorf("discover manifests: %w", err)
	}
	var jsManagers = map[string][]string{}
	for _, rel := range manifests {
		dir := filepath.Dir(rel)
		base := filepath.Base(rel)
		full := filepath.Join(absolute, rel)
		switch base {
		case "go.mod":
			report.Detections = append(report.Detections, Detection{"Go", "language", []string{rel}})
			report.TestCommands = append(report.TestCommands, TestCommand{Directory: dir, Executable: "go", Arguments: []string{"test", "./..."}})
		case "package.json":
			report.Detections = append(report.Detections, Detection{"Node.js", "ecosystem", []string{rel}})
			pkg, e := parsePackage(full)
			if e != nil {
				report.add(Warning, "MANIFEST_INVALID", "Cannot parse package.json: "+e.Error(), "Validate JSON syntax and ensure the manifest is not oversized.", rel)
				continue
			}
			for _, entry := range []struct{ dep, name string }{
				{"react", "React"}, {"next", "Next.js"}, {"vue", "Vue"}, {"@angular/core", "Angular"},
				{"vite", "Vite"}, {"express", "Express"}, {"vitest", "Vitest"}, {"jest", "Jest"},
				{"typescript", "TypeScript"},
			} {
				if pkg.hasDependency(entry.dep) {
					report.Detections = append(report.Detections, Detection{entry.name, "framework/tool", []string{rel}})
				}
			}
			if _, ok := pkg.Scripts["test"]; ok {
				// Never execute an arbitrary package script without explicit consent.
				report.TestCommands = append(report.TestCommands, TestCommand{Directory: dir, Executable: "npm", Arguments: []string{"test"}})
			}
			for _, name := range []string{"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb"} {
				candidate := filepath.Join(dir, name)
				if _, ok := manifestsSet(manifests)[candidate]; ok {
					jsManagers[dir] = append(jsManagers[dir], name)
				}
			}
		case "pyproject.toml":
			report.Detections = append(report.Detections, Detection{"Python", "language", []string{rel}})
		case "requirements.txt":
			report.Detections = append(report.Detections, Detection{"Python requirements", "dependencies", []string{rel}})
		case "Cargo.toml":
			report.Detections = append(report.Detections, Detection{"Rust", "language", []string{rel}})
		case "pom.xml":
			report.Detections = append(report.Detections, Detection{"Maven", "build", []string{rel}})
		case "build.gradle", "build.gradle.kts":
			report.Detections = append(report.Detections, Detection{"Gradle", "build", []string{rel}})
		case "compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml":
			report.Detections = append(report.Detections, Detection{"Docker Compose", "service", []string{rel}})
		default:
			if strings.HasSuffix(base, ".csproj") || strings.HasSuffix(base, ".sln") {
				report.Detections = append(report.Detections, Detection{".NET", "ecosystem", []string{rel}})
			}
		}
	}
	for dir, locks := range jsManagers {
		if len(locks) > 1 {
			sort.Strings(locks)
			report.add(Warning, "MULTIPLE_LOCKFILES", "Multiple JavaScript package manager lockfiles found.", "Keep the lockfile for the package manager used by this project and remove obsolete ones after review.", joinPaths(dir, locks)...)
		}
	}
	if len(report.Detections) == 0 {
		report.add(Info, "NO_MANIFEST", "No supported project manifest found in the workspace or its first two directory levels.", "Open the project root or check whether this project uses an unsupported build system.")
	}
	inspectEnv(absolute, manifests, &report)
	inspectGit(ctx, absolute, &report)
	sort.Slice(report.Detections, func(i, j int) bool {
		if report.Detections[i].Name == report.Detections[j].Name {
			return report.Detections[i].Evidence[0] < report.Detections[j].Evidence[0]
		}
		return report.Detections[i].Name < report.Detections[j].Name
	})
	sort.Slice(report.TestCommands, func(i, j int) bool { return report.TestCommands[i].Directory < report.TestCommands[j].Directory })
	if opts.RunTests {
		for _, candidate := range report.TestCommands {
			result := executeTest(ctx, absolute, candidate, opts.Timeout)
			report.TestResults = append(report.TestResults, result)
			if !result.Passed {
				reason := "Test command failed."
				if result.TimedOut {
					reason = "Test command timed out."
				}
				report.add(Error, "TEST_FAILED", reason, "Inspect test output and reproduce the indicated command in a trusted workspace.", candidate.Directory)
			}
		}
		if len(report.TestCommands) == 0 {
			report.add(Info, "NO_TEST_COMMAND", "No supported test command was discovered.", "Configure a Go module or a package.json test script.")
		}
	}
	return report, nil
}

func manifestsSet(paths []string) map[string]struct{} {
	out := make(map[string]struct{}, len(paths))
	for _, path := range paths {
		out[path] = struct{}{}
	}
	return out
}
func joinPaths(dir string, names []string) []string {
	out := make([]string, 0, len(names))
	for _, n := range names {
		out = append(out, filepath.ToSlash(filepath.Join(dir, n)))
	}
	return out
}

// discover only reads directory metadata; symlinks, hidden directories and
// dependency/build caches are never traversed.
func discover(root string) ([]string, error) {
	allowed := map[string]bool{"go.mod": true, "package.json": true, "package-lock.json": true, "pnpm-lock.yaml": true, "yarn.lock": true, "bun.lock": true, "bun.lockb": true, "pyproject.toml": true, "requirements.txt": true, "Cargo.toml": true, "pom.xml": true, "build.gradle": true, "build.gradle.kts": true, "compose.yml": true, "compose.yaml": true, "docker-compose.yml": true, "docker-compose.yaml": true, ".env.example": true, ".env.sample": true, ".gitignore": true}
	ignored := map[string]bool{"node_modules": true, "vendor": true, "dist": true, "build": true, "target": true, ".git": true, ".venv": true, "venv": true, ".next": true, "__pycache__": true}
	var paths []string
	var walk func(string, int) error
	walk = func(dir string, depth int) error {
		entries, err := os.ReadDir(filepath.Join(root, dir))
		if err != nil {
			return err
		}
		for _, entry := range entries {
			name := entry.Name()
			rel := filepath.Join(dir, name)
			if entry.Type()&os.ModeSymlink != 0 {
				continue
			}
			if entry.IsDir() {
				if depth < 2 && !ignored[name] && !strings.HasPrefix(name, ".") {
					if err := walk(rel, depth+1); err != nil {
						return err
					}
				}
				continue
			}
			if allowed[name] || strings.HasSuffix(name, ".csproj") || strings.HasSuffix(name, ".sln") {
				paths = append(paths, rel)
			}
		}
		return nil
	}
	if err := walk(".", 0); err != nil {
		return nil, err
	}
	sort.Strings(paths)
	return paths, nil
}

type packageJSON struct {
	Scripts         map[string]string          `json:"scripts"`
	Dependencies    map[string]json.RawMessage `json:"dependencies"`
	DevDependencies map[string]json.RawMessage `json:"devDependencies"`
}

func (p packageJSON) hasDependency(n string) bool {
	_, ok := p.Dependencies[n]
	if ok {
		return true
	}
	_, ok = p.DevDependencies[n]
	return ok
}
func parsePackage(path string) (packageJSON, error) {
	var out packageJSON
	f, err := os.Open(path)
	if err != nil {
		return out, err
	}
	defer f.Close()
	info, err := f.Stat()
	if err != nil {
		return out, err
	}
	if info.Size() > maxManifestBytes {
		return out, fmt.Errorf("manifest exceeds %d bytes", maxManifestBytes)
	}
	data, err := io.ReadAll(io.LimitReader(f, maxManifestBytes+1))
	if err != nil {
		return out, err
	}
	if len(data) > maxManifestBytes {
		return out, fmt.Errorf("manifest exceeds %d bytes", maxManifestBytes)
	}
	if err := json.Unmarshal(data, &out); err != nil {
		return out, fmt.Errorf("invalid JSON")
	}
	return out, nil
}

func inspectEnv(root string, manifests []string, r *Report) {
	for _, path := range manifests {
		if !strings.HasSuffix(path, ".env.example") && !strings.HasSuffix(path, ".env.sample") {
			continue
		}
		// Read only variable *names*. Values from secret templates must never
		// appear in findings or output, even when malformed.
		file, err := os.Open(filepath.Join(root, path))
		if err != nil {
			r.add(Warning, "ENV_TEMPLATE_UNREADABLE", "Cannot read environment template.", "Verify file permissions.", path)
			continue
		}
		data, err := io.ReadAll(io.LimitReader(file, maxManifestBytes+1))
		file.Close()
		if err != nil {
			r.add(Warning, "ENV_TEMPLATE_UNREADABLE", "Cannot read environment template.", "Verify file permissions.", path)
			continue
		}
		if len(data) > maxManifestBytes {
			r.add(Warning, "ENV_TEMPLATE_LARGE", "Environment template exceeds inspection limit.", "Review the template manually.", path)
			continue
		}
		names := map[string]bool{}
		for _, line := range strings.Split(string(data), "\n") {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, "export ") {
				line = strings.TrimSpace(strings.TrimPrefix(line, "export "))
			}
			index := strings.IndexByte(line, '=')
			if index < 1 {
				continue
			}
			key := strings.TrimSpace(line[:index])
			if isVariableName(key) {
				names[key] = true
			}
		}
		if len(names) > 0 {
			r.add(Info, "ENV_TEMPLATE_FOUND", fmt.Sprintf("Environment template documents %d variable(s); values were not read into the report.", len(names)), "Review this template and configure variables using your project's documented setup.", path)
		}
	}
}
func isVariableName(s string) bool {
	if s == "" {
		return false
	}
	for i, c := range s {
		if (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || c == '_' || (i > 0 && c >= '0' && c <= '9') {
			continue
		}
		return false
	}
	return true
}

func inspectGit(ctx context.Context, root string, r *Report) {
	if _, err := exec.LookPath("git"); err != nil {
		r.add(Info, "GIT_UNAVAILABLE", "Git executable is not on PATH.", "Install Git to enable repository checks.")
		return
	}
	ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	check := exec.CommandContext(ctx, "git", "rev-parse", "--is-inside-work-tree")
	check.Dir = root
	raw, err := check.Output()
	if err != nil || strings.TrimSpace(string(raw)) != "true" {
		r.add(Info, "NOT_GIT_REPOSITORY", "Workspace is not inside a Git worktree.", "Run git init if this project should be version controlled.")
		return
	}
	status := exec.CommandContext(ctx, "git", "status", "--porcelain=v1", "--untracked-files=no")
	status.Dir = root
	data, err := status.Output()
	if err != nil {
		r.add(Warning, "GIT_STATUS_UNAVAILABLE", "Unable to read Git status.", "Run git status to inspect the repository.")
		return
	}
	if len(data) > 0 {
		r.add(Info, "GIT_MODIFIED", "Git reports modifications to tracked files.", "Review git status before committing.")
	}
	// Restrict the tracked secrets query to exact relative names; never print values.
	tracked := exec.CommandContext(ctx, "git", "ls-files", "--cached", "--", ".env")
	tracked.Dir = root
	output, err := tracked.Output()
	if err == nil && strings.TrimSpace(string(output)) == ".env" {
		r.add(Warning, "TRACKED_ENV", ".env is tracked by Git and may contain credentials.", "Remove sensitive data and rotate exposed credentials; use a template such as .env.example instead.", ".env")
	}
}

// limitedOutput discards bytes beyond the configured cap while still reporting
// the full number written. No untrusted test process can grow our log buffer.
type limitedOutput struct {
	mu        sync.Mutex
	max       int
	bytes     []byte
	truncated bool
}

func (o *limitedOutput) Write(p []byte) (int, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	n := len(p)
	left := o.max - len(o.bytes)
	if left > 0 {
		if left > n {
			left = n
		}
		o.bytes = append(o.bytes, p[:left]...)
	}
	if n > left {
		o.truncated = true
	}
	return n, nil
}
func (o *limitedOutput) String() string {
	o.mu.Lock()
	defer o.mu.Unlock()
	value := string(o.bytes)
	if o.truncated {
		value += "\n[output truncated]"
	}
	return value
}

var secretAssignment = regexp.MustCompile(`(?i)(\b(?:api[_-]?key|token|password|secret|authorization|credential)[\w-]*\s*[:=]\s*)([^\s]+)`)
var githubSecret = regexp.MustCompile(`\b(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]+\b`)

func redactSecrets(value string) string {
	// Replace secret-like environment values if the invoked test prints them.
	// Do not disclose any environment variable values in diagnostic output.
	for _, entry := range os.Environ() {
		key, secret, ok := strings.Cut(entry, "=")
		if !ok || len(secret) < 4 {
			continue
		}
		name := strings.ToLower(key)
		for _, needle := range []string{"token", "secret", "password", "passwd", "api_key", "apikey", "credential", "private_key", "access_key"} {
			if strings.Contains(name, needle) {
				value = strings.ReplaceAll(value, secret, "[REDACTED]")
				break
			}
		}
	}
	value = githubSecret.ReplaceAllString(value, "[REDACTED]")
	return secretAssignment.ReplaceAllString(value, "${1}[REDACTED]")
}

func executeTest(parent context.Context, root string, task TestCommand, timeout time.Duration) TestResult {
	result := TestResult{Command: task}
	ctx, cancel := context.WithTimeout(parent, timeout)
	defer cancel()
	executable, err := exec.LookPath(task.Executable)
	if err != nil {
		result.Output = "Required executable is not installed: " + task.Executable
		return result
	}
	cmd := exec.CommandContext(ctx, executable, task.Arguments...)
	cmd.Dir = filepath.Join(root, task.Directory)
	// CI disables interactive watch behavior for popular JS test frameworks.
	cmd.Env = append(os.Environ(), "CI=true")
	output := &limitedOutput{max: maxTestOutputBytes}
	cmd.Stdout = output
	cmd.Stderr = output
	err = cmd.Run()
	result.Output = redactSecrets(output.String())
	result.TimedOut = errors.Is(ctx.Err(), context.DeadlineExceeded)
	result.Passed = err == nil && !result.TimedOut
	return result
}
