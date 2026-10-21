package safepath

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestEnsureUnlinkedPathAllowsCleanNestedDirectory(t *testing.T) {
	project := filepath.Join(t.TempDir(), "sub", "project")
	if err := os.MkdirAll(project, 0700); err != nil {
		t.Fatal(err)
	}
	if err := EnsureUnlinkedPath(project); err != nil {
		t.Fatalf("clean path rejected: %v", err)
	}
}

func TestEnsureUnlinkedPathRejectsLinkedAncestorAndRoot(t *testing.T) {
	base := t.TempDir()
	real := filepath.Join(base, "real")
	project := filepath.Join(real, "project")
	if err := os.MkdirAll(project, 0700); err != nil {
		t.Fatal(err)
	}
	linked := filepath.Join(base, "linked")
	if err := os.Symlink(real, linked); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	for _, candidate := range []string{linked, filepath.Join(linked, "project")} {
		if err := EnsureUnlinkedPath(candidate); !errors.Is(err, ErrLinkedPath) {
			t.Errorf("expected linked-path error for %q, got %v", candidate, err)
		}
	}
	if err := EnsureUnlinkedPath(project); err != nil {
		t.Fatalf("real directory rejected: %v", err)
	}
}

func TestEnsureUnlinkedPathRejectsRelativeAndMissingPaths(t *testing.T) {
	for _, path := range []string{"relative/path", filepath.Join(t.TempDir(), "missing")} {
		if err := EnsureUnlinkedPath(path); err == nil {
			t.Errorf("invalid path %q accepted", path)
		}
	}
}
