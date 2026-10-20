package doctor

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func put(t *testing.T, root, name, contents string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(root, name), []byte(contents), 0600); err != nil {
		t.Fatal(err)
	}
}
func includes(items []string, item string) bool {
	for _, s := range items {
		if s == item {
			return true
		}
	}
	return false
}
func finding(r Report, code string) bool {
	for _, f := range r.Findings {
		if f.Code == code {
			return true
		}
	}
	return false
}

func TestGoProject(t *testing.T) {
	root := t.TempDir()
	put(t, root, "go.mod", "module example.com/demo\ngo 1.22\n")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !includes(r.Languages, "Go") || len(r.TestCommands) != 1 || r.TestCommands[0].Tool != "go" {
		t.Fatalf("unexpected detection: %+v", r)
	}
	if finding(r, "unknown-project") {
		t.Fatal("known project reported unknown")
	}
}
func TestNodeProjectAndConflictingLocks(t *testing.T) {
	root := t.TempDir()
	put(t, root, "package.json", `{"scripts":{"test":"vitest run"},"devDependencies":{"typescript":"*","vite":"*"},"dependencies":{"react":"*"}}`)
	put(t, root, "package-lock.json", "{}")
	put(t, root, "yarn.lock", "")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !includes(r.Frameworks, "React") || !includes(r.Frameworks, "TypeScript") || !finding(r, "multiple-lockfiles") {
		t.Fatalf("unexpected detection: %+v", r)
	}
	if len(r.TestCommands) != 1 || r.TestCommands[0].Tool != "npm" {
		t.Fatalf("test detection: %+v", r.TestCommands)
	}
}
func TestMalformedManifest(t *testing.T) {
	root := t.TempDir()
	put(t, root, "package.json", "{")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(r, "package-json-invalid") {
		t.Fatalf("missing invalid JSON finding: %+v", r)
	}
}
func TestNoFollowingManifestSymlinks(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	put(t, outside, "package.json", `{"dependencies":{"react":"*"}}`)
	if err := os.Symlink(filepath.Join(outside, "package.json"), filepath.Join(root, "package.json")); err != nil {
		t.Skipf("symlinks unsupported: %v", err)
	}
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Languages) != 0 || !finding(r, "unknown-project") {
		t.Fatalf("followed symlink: %+v", r)
	}
}
func TestEnvTemplateDoesNotLeakValues(t *testing.T) {
	root := t.TempDir()
	put(t, root, ".env.example", "API_KEY=super-secret-value\n#COMMENT=not-a-key\n")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(r, "env-template") {
		t.Fatalf("missing environment finding: %+v", r)
	}
	for _, f := range r.Findings {
		if strings.Contains(f.Evidence, "super-secret-value") {
			t.Fatalf("leaked value: %+v", f)
		}
	}
}
func TestInvalidWorkspace(t *testing.T) {
	_, err := Inspect(filepath.Join(t.TempDir(), "missing"))
	if err == nil {
		t.Fatal("expected error")
	}
}
