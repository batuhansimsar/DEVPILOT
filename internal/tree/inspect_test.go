package tree

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func write(t *testing.T, root, name string) {
	t.Helper()
	p := filepath.Join(root, name)
	if err := os.MkdirAll(filepath.Dir(p), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte("x"), 0600); err != nil {
		t.Fatal(err)
	}
}
func found(r Report, name string) bool {
	for _, e := range r.Entries {
		if e.Path == name {
			return true
		}
	}
	return false
}
func TestTreeSkipsDepsAndDepth(t *testing.T) {
	d := t.TempDir()
	write(t, d, "src/pkg/main.go")
	write(t, d, "node_modules/pkg/index.js")
	write(t, d, ".github/workflows/ci.yml")
	r, err := Inspect(d, 2, 100)
	if err != nil {
		t.Fatal(err)
	}
	if !found(r, "src/pkg") || found(r, "src/pkg/main.go") || found(r, "node_modules") || !found(r, ".github/workflows") {
		t.Fatalf("unexpected entries: %+v", r.Entries)
	}
}
func TestSymlinksNeverFollowed(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink privilege")
	}
	d := t.TempDir()
	out := t.TempDir()
	write(t, out, "secret.txt")
	if err := os.Symlink(out, filepath.Join(d, "external")); err != nil {
		t.Skip(err)
	}
	r, err := Inspect(d, 4, 100)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Entries) != 1 || r.Entries[0].Kind != "symlink" {
		t.Fatalf("symlink followed: %+v", r.Entries)
	}
}
func TestBoundedAndInvalid(t *testing.T) {
	d := t.TempDir()
	write(t, d, "a")
	write(t, d, "b")
	r, err := Inspect(d, 3, 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Entries) != 1 || !r.Truncated {
		t.Fatalf("limit not honored: %+v", r)
	}
	for _, cfg := range []struct{ d, m int }{{0, 1}, {11, 1}, {1, 0}, {1, 2001}} {
		if _, err := Inspect(d, cfg.d, cfg.m); err == nil {
			t.Fatalf("expected error for %+v", cfg)
		}
	}
	write(t, d, "afile")
	if _, err := Inspect(filepath.Join(d, "afile"), 1, 2); err == nil {
		t.Fatal("file should not be workspace")
	}
}
