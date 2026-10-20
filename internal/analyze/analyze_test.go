package analyze

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func write(t *testing.T, path, value string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(value), 0600); err != nil {
		t.Fatal(err)
	}
}

func TestAnalyzeNestedWorkspaceAndCI(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "web", "package.json"), `{"name":"web"}`)
	write(t, filepath.Join(root, "web", "src", "main.ts"), "export const x = 1")
	write(t, filepath.Join(root, "api", "go.mod"), "module example.com/api")
	write(t, filepath.Join(root, "api", "main.go"), "package main")
	write(t, filepath.Join(root, ".github", "workflows", "ci.yml"), "name: CI")
	write(t, filepath.Join(root, "node_modules", "ignored.ts"), "x")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if r.FileCount != 5 {
		t.Fatalf("count %d", r.FileCount)
	}
	if len(r.Manifests) != 2 || len(r.CI) != 1 {
		t.Fatalf("report: %+v", r)
	}
	if len(r.Languages) != 2 {
		t.Fatalf("languages: %+v", r.Languages)
	}
}

func TestSymlinkNeverTraversed(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink privileges")
	}
	root := t.TempDir()
	outside := t.TempDir()
	write(t, filepath.Join(outside, "secret.ts"), "do not read")
	if err := os.Symlink(outside, filepath.Join(root, "linked")); err != nil {
		t.Fatal(err)
	}
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if r.FileCount != 0 {
		t.Fatalf("followed symlink: %+v", r)
	}
}

func TestInvalidRoot(t *testing.T) {
	root := t.TempDir()
	file := filepath.Join(root, "file.txt")
	write(t, file, "x")
	if _, err := Inspect(file); err == nil {
		t.Fatal("expected error")
	}
}

func TestReportNeverIncludesFileContents(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "secret.py"), "TOP_SECRET_PASSWORD")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(strings.Join(r.Manifests, " "), "TOP_SECRET") || len(r.Languages) != 1 {
		t.Fatalf("unexpected report: %+v", r)
	}
}
