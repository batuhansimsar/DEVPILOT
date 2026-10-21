package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestToxOnlyPythonProject(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "tox.ini"), []byte("[tox]\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if !hasPythonProjectMarker(root) {
		t.Fatal("tox.ini must identify a Python project")
	}
}

func TestToxMarkerRejectsDirectoryAndSymlink(t *testing.T) {
	root := t.TempDir()
	marker := filepath.Join(root, "tox.ini")
	if err := os.Mkdir(marker, 0700); err != nil {
		t.Fatal(err)
	}
	if hasPythonProjectMarker(root) {
		t.Fatal("directory must not be treated as tox.ini")
	}
	if err := os.Remove(marker); err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(root, "target")
	if err := os.WriteFile(target, []byte("[tox]\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, marker); err != nil {
		t.Skipf("symlink unavailable: %v", err)
	}
	if hasPythonProjectMarker(root) {
		t.Fatal("symlink must not be treated as tox.ini")
	}
}
