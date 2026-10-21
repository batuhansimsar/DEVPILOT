package analyze

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestProjectRootValidatesDirectory(t *testing.T) {
	dir := t.TempDir()
	got, err := projectRoot(dir)
	if err != nil || got != dir {
		t.Fatalf("projectRoot(%q) = %q, %v", dir, got, err)
	}

	file := filepath.Join(dir, "file.txt")
	if err := os.WriteFile(file, []byte("x"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := projectRoot(file); err == nil {
		t.Fatal("regular file accepted as a project directory")
	}
	if _, err := projectRoot(filepath.Join(dir, "missing")); err == nil {
		t.Fatal("missing directory accepted")
	}
}

func TestProjectRootRejectsSymlink(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink creation may require elevated privileges")
	}
	dir := t.TempDir()
	link := filepath.Join(t.TempDir(), "linked-root")
	if err := os.Symlink(dir, link); err != nil {
		t.Fatal(err)
	}
	if _, err := projectRoot(link); err == nil {
		t.Fatal("project root symlink must be rejected before inspection")
	}
}
