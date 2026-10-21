package doctor

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestValidateProjectRoot(t *testing.T) {
	root := t.TempDir()
	got, err := validateProjectRoot(root)
	if err != nil || got != root {
		t.Fatalf("validateProjectRoot(%q) = %q, %v", root, got, err)
	}

	file := filepath.Join(root, "file.txt")
	if err := os.WriteFile(file, []byte("hello"), 0600); err != nil {
		t.Fatal(err)
	}
	for _, path := range []string{file, filepath.Join(root, "absent")} {
		if _, err := validateProjectRoot(path); err == nil {
			t.Errorf("accepted a non-directory root: %q", path)
		}
	}
}

func TestValidateProjectRootRejectsSymlink(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink creation may require elevated privileges")
	}
	root := t.TempDir()
	link := filepath.Join(t.TempDir(), "link")
	if err := os.Symlink(root, link); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	if _, err := validateProjectRoot(link); err == nil {
		t.Fatal("accepted a symbolic link to a project directory")
	}
}
