package doctor

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func write(t *testing.T, root, file, content string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(root, file), []byte(content), 0600); err != nil {
		t.Fatal(err)
	}
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
	dir := t.TempDir()
	write(t, dir, "go.mod", "module example.com/a\ngo 1.23\n")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Languages) != 1 || r.Languages[0] != "Go" {
		t.Fatalf("languages: %v", r.Languages)
	}
	if r.Tests == nil || r.Tests.Executable != "go" || strings.Join(r.Tests.Arguments, " ") != "test ./..." {
		t.Fatalf("test: %+v", r.Tests)
	}
}
func TestNodeDetectionAndInvalidJSON(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "package.json", `{"dependencies":{"react":"*","vite":"*"},"scripts":{"test":"vitest run"}}`)
	write(t, dir, "pnpm-lock.yaml", "lockfileVersion: '9.0'")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if r.PackageManager != "pnpm" || r.Tests == nil || r.Tests.Executable != "pnpm" {
		t.Fatalf("result: %+v", r)
	}
	if strings.Join(r.Frameworks, ",") != "React,Vite" {
		t.Fatalf("frameworks: %v", r.Frameworks)
	}
	write(t, dir, "package.json", "{")
	r, err = Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(r, "package-json-invalid") {
		t.Fatalf("missing invalid-json finding: %+v", r.Findings)
	}
}
func TestEnvNamesOnly(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, ".env.example", "API_KEY=secret-example\nDB_URL=postgres://password\n# ignored=comment\n")
	write(t, dir, ".env", "API_KEY=live-secret\n")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(r, "env-local-missing-keys") {
		t.Fatal("missing key diagnostic")
	}
	for _, f := range r.Findings {
		if strings.Contains(f.Message, "secret") || strings.Contains(f.Message, "password") || strings.Contains(f.Message, "live-") {
			t.Fatalf("value leaked: %+v", f)
		}
	}
}
func TestSymlinkNotRead(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink permissions on Windows")
	}
	dir := t.TempDir()
	outside := filepath.Join(t.TempDir(), "outside.json")
	if err := os.WriteFile(outside, []byte(`{"dependencies":{"react":"secret"}}`), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(dir, "package.json")); err != nil {
		t.Fatal(err)
	}
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Languages) != 0 {
		t.Fatalf("symlink must not infer language: %v", r.Languages)
	}
}
func TestOversizedPackageJSON(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "package.json", strings.Repeat("a", 1024*1024+1))
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(r, "package-json-unreadable") {
		t.Fatalf("expected warning: %+v", r.Findings)
	}
}
func TestNotDirectory(t *testing.T) {
	p := filepath.Join(t.TempDir(), "file")
	write(t, filepath.Dir(p), "file", "text")
	if _, err := Inspect(p); err == nil {
		t.Fatal("expected error")
	}
}
