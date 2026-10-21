package safepath

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
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

func TestEnsureUnlinkedPathRejectsNonDirectoryRootWithoutLeakingPath(t *testing.T) {
	base := t.TempDir()
	file := filepath.Join(base, "private-project-name.txt")
	if err := os.WriteFile(file, []byte("data"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := EnsureUnlinkedPath(file); err == nil {
		t.Fatal("regular file accepted as project root")
	} else if strings.Contains(err.Error(), base) || strings.Contains(err.Error(), filepath.Base(file)) {
		t.Fatalf("path leaked into diagnostic: %v", err)
	}
	if err := EnsureUnlinkedPath(base); err != nil {
		t.Fatalf("parent directory rejected: %v", err)
	}
}
