package doctor

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func write(t *testing.T, root, rel, content string) {
	t.Helper()
	path := filepath.Join(root, rel)
	if e := os.MkdirAll(filepath.Dir(path), 0755); e != nil {
		t.Fatal(e)
	}
	if e := os.WriteFile(path, []byte(content), 0644); e != nil {
		t.Fatal(e)
	}
}
func hasFinding(r Report, code string) bool {
	for _, f := range r.Findings {
		if f.Code == code {
			return true
		}
	}
	return false
}

func TestAnalyzeEmpty(t *testing.T) {
	r, e := Analyze(t.TempDir())
	if e != nil {
		t.Fatal(e)
	}
	if len(r.Projects) != 0 || len(r.Tests) != 0 || !hasFinding(r, "NO_PROJECT_MANIFEST") {
		t.Fatalf("unexpected report: %+v", r)
	}
}
func TestAnalyzeGoAndNestedNode(t *testing.T) {
	root := t.TempDir()
	write(t, root, "go.mod", "module example.org/app\n\ngo 1.23\n")
	write(t, root, "frontend/package.json", `{"dependencies":{"react":"^19.0.0","next":"^15.0.0"},"scripts":{"test":"vitest run"}}`)
	write(t, root, "frontend/pnpm-lock.yaml", "lockfileVersion: 9.0")
	write(t, root, "frontend/.env.example", "SUPER_SECRET_KEY=private_example_value\n")
	write(t, root, ".git/HEAD", "ref: refs/heads/feature/doctor\n")
	r, e := Analyze(root)
	if e != nil {
		t.Fatal(e)
	}
	if len(r.Projects) != 2 || len(r.Tests) != 2 {
		t.Fatalf("expected two projects and tests: %+v", r)
	}
	if r.Git.Branch != "feature/doctor" {
		t.Fatalf("wrong branch: %+v", r.Git)
	}
	if !hasFinding(r, "ENV_TEMPLATE_FOUND") {
		t.Fatal("missing env template finding")
	}
	found := false
	for _, p := range r.Projects {
		if p.Directory == "frontend" {
			found = strings.Join(p.Frameworks, ",") == "next,react"
		}
	}
	if !found {
		t.Fatalf("framework detection failed: %+v", r.Projects)
	}
	buf, e := json.Marshal(r)
	if e != nil {
		t.Fatal(e)
	}
	if strings.Contains(string(buf), "private_example_value") {
		t.Fatal("environment sample values were exposed")
	}
}
func TestConflictAndInvalidManifest(t *testing.T) {
	root := t.TempDir()
	write(t, root, "package.json", "{not json")
	write(t, root, "yarn.lock", "")
	write(t, root, "package-lock.json", "{}")
	r, e := Analyze(root)
	if e != nil {
		t.Fatal(e)
	}
	if !hasFinding(r, "INVALID_PACKAGE_JSON") || !hasFinding(r, "CONFLICTING_LOCKFILES") {
		t.Fatalf("findings: %+v", r.Findings)
	}
	if len(r.Tests) != 0 {
		t.Fatalf("malformed package should not create test command: %+v", r.Tests)
	}
}
func TestIgnoreExternalSymlink(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink privileges differ on Windows")
	}
	root := t.TempDir()
	outside := t.TempDir()
	write(t, outside, "package.json", `{"scripts":{"test":"npm test"}}`)
	if e := os.Symlink(outside, filepath.Join(root, "linked")); e != nil {
		t.Fatal(e)
	}
	r, e := Analyze(root)
	if e != nil {
		t.Fatal(e)
	}
	if len(r.Projects) != 0 {
		t.Fatalf("followed untrusted symlink: %+v", r.Projects)
	}
}
func TestDotnetDiscovery(t *testing.T) {
	root := t.TempDir()
	write(t, root, "src/App.csproj", "<Project Sdk=\"Microsoft.NET.Sdk\"></Project>")
	write(t, root, "tests/App.Tests.csproj", "<Project><PropertyGroup><IsTestProject>true</IsTestProject></PropertyGroup></Project>")
	r, e := Analyze(root)
	if e != nil {
		t.Fatal(e)
	}
	if len(r.Tests) != 1 || r.Tests[0].Program != "dotnet" {
		t.Fatalf("dotnet detection: %+v", r.Tests)
	}
}
func TestNoPlaceholderNodeTest(t *testing.T) {
	root := t.TempDir()
	write(t, root, "package.json", `{"scripts":{"test":"echo \"Error: no test specified\" && exit 1"}}`)
	r, e := Analyze(root)
	if e != nil {
		t.Fatal(e)
	}
	if len(r.Tests) != 0 {
		t.Fatalf("discovered placeholder script: %+v", r.Tests)
	}
}
