package projecttree

import (
	"os"
	"path/filepath"
	"testing"
)

func mkdir(t *testing.T, root, name string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Join(root, name), 0700); err != nil {
		t.Fatal(err)
	}
}
func file(t *testing.T, root, name string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(root, name), []byte("x"), 0600); err != nil {
		t.Fatal(err)
	}
}
func TestScanIgnoresLargeAndSecretDirectories(t *testing.T) {
	root := t.TempDir()
	mkdir(t, root, "src/nested")
	file(t, root, "src/main.go")
	mkdir(t, root, "node_modules/pkg")
	file(t, root, "node_modules/pkg/ignored.js")
	file(t, root, ".env.local")
	file(t, root, "credentials.json")
	r, err := Scan(root, 3, 100)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Entries) != 3 {
		t.Fatalf("expected src, main.go and nested only; got %#v", r.Entries)
	}
	if r.Entries[0].Path != "src" {
		t.Fatalf("unexpected ordering: %+v", r.Entries)
	}
	for _, e := range r.Entries {
		if e.Path == "credentials.json" || e.Path == ".env.local" {
			t.Fatal("secret name exposed")
		}
	}
}
func TestDepthAndEntryBounds(t *testing.T) {
	root := t.TempDir()
	mkdir(t, root, "a/b")
	file(t, root, "a/one.go")
	file(t, root, "a/b/two.go")
	shallow, err := Scan(root, 1, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(shallow.Entries) != 1 || shallow.Entries[0].Path != "a" {
		t.Fatalf("depth: %#v", shallow.Entries)
	}
	limited, err := Scan(root, 3, 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(limited.Entries) != 1 || !limited.Truncated {
		t.Fatalf("bounds: %+v", limited)
	}
}
func TestSymlinkTargetNotTraversed(t *testing.T) {
	root := t.TempDir()
	external := t.TempDir()
	file(t, external, "outside.txt")
	if err := os.Symlink(external, filepath.Join(root, "link")); err != nil {
		t.Skip(err)
	}
	r, err := Scan(root, 4, 50)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Entries) != 1 || r.Entries[0].Kind != "symlink" {
		t.Fatalf("symlink: %+v", r.Entries)
	}
}
func TestRejectInvalidSettings(t *testing.T) {
	root := t.TempDir()
	for _, tc := range [][2]int{{0, 10}, {11, 10}, {1, 0}, {1, 2001}} {
		if _, err := Scan(root, tc[0], tc[1]); err == nil {
			t.Fatalf("accepted invalid settings: %v", tc)
		}
	}
	if _, err := Scan(filepath.Join(root, "missing"), 1, 10); err == nil {
		t.Fatal("accepted missing path")
	}
}
