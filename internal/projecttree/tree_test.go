package projecttree

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

func mk(t *testing.T, root, path string) {
	t.Helper()
	full := filepath.Join(root, path)
	if err := os.MkdirAll(filepath.Dir(full), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(full, []byte("example"), 0600); err != nil {
		t.Fatal(err)
	}
}

func TestWalkAndIgnoredDirectories(t *testing.T) {
	root := t.TempDir()
	mk(t, root, "src/app/main.go")
	mk(t, root, "src/README.md")
	mk(t, root, "node_modules/pkg/malicious.js")
	mk(t, root, ".git/config")
	m, err := MapDirectory(root, 3)
	if err != nil {
		t.Fatal(err)
	}
	if m.Truncated || len(m.Entries) != 4 {
		t.Fatalf("entries=%+v", m)
	}
	if m.Entries[0].Path != "src" || m.Entries[1].Path != "src/README.md" || m.Entries[2].Path != "src/app" || m.Entries[3].Path != "src/app/main.go" {
		t.Fatalf("entries=%+v", m.Entries)
	}
	if len(m.SkippedDirectories) != 2 {
		t.Fatalf("skipped=%v", m.SkippedDirectories)
	}
}

func TestDepthDoesNotRecurse(t *testing.T) {
	root := t.TempDir()
	mk(t, root, "a/b/c.txt")
	m, err := MapDirectory(root, 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(m.Entries) != 1 || m.Entries[0].Path != "a" {
		t.Fatalf("entries=%+v", m.Entries)
	}
}

func TestSymlinkNotTraversed(t *testing.T) {
	root, other := t.TempDir(), t.TempDir()
	mk(t, other, "secret.txt")
	if err := os.Symlink(other, filepath.Join(root, "linked")); err != nil {
		t.Skipf("symlink unsupported: %v", err)
	}
	m, err := MapDirectory(root, 3)
	if err != nil {
		t.Fatal(err)
	}
	if len(m.Entries) != 1 || m.Entries[0].Type != "symlink" || strings.Contains(m.Entries[0].Path, "secret") {
		t.Fatalf("entries=%+v", m.Entries)
	}
}

func TestRejectInvalidRootsAndDepth(t *testing.T) {
	root := t.TempDir()
	if _, err := MapDirectory(root, 0); err == nil {
		t.Fatal("depth 0 accepted")
	}
	if _, err := MapDirectory(root, MaxDepth+1); err == nil {
		t.Fatal("oversized depth accepted")
	}
	mk(t, root, "file.txt")
	if _, err := MapDirectory(filepath.Join(root, "file.txt"), 3); err == nil {
		t.Fatal("file accepted as root")
	}
}

func TestTruncationLimit(t *testing.T) {
	root := t.TempDir()
	for i := 0; i < MaxEntries+3; i++ {
		mk(t, root, fmtName(i))
	}
	m, err := MapDirectory(root, 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(m.Entries) != MaxEntries || !m.Truncated {
		t.Fatalf("entries=%d truncated=%v", len(m.Entries), m.Truncated)
	}
}

func fmtName(i int) string { return strconv.Itoa(i) + ".txt" }
