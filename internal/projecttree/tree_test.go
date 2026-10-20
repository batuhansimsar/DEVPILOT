package projecttree

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func mkdir(t *testing.T, p string) {
	t.Helper()
	if e := os.MkdirAll(p, 0700); e != nil {
		t.Fatal(e)
	}
}
func file(t *testing.T, p string) {
	t.Helper()
	if e := os.WriteFile(p, []byte("fixture"), 0600); e != nil {
		t.Fatal(e)
	}
}
func TestTreeOrdersAndLimits(t *testing.T) {
	root := t.TempDir()
	mkdir(t, filepath.Join(root, "src"))
	file(t, filepath.Join(root, "b.go"))
	file(t, filepath.Join(root, "a.go"))
	file(t, filepath.Join(root, "src", "one.go"))
	r, e := Scan(root, Options{MaxDepth: 3, MaxEntries: 20})
	if e != nil {
		t.Fatal(e)
	}
	got := []string{}
	for _, v := range r.Entries {
		got = append(got, v.Path)
	}
	if strings.Join(got, ",") != "a.go,b.go,src,src/one.go" {
		t.Fatalf("got %v", got)
	}
	limited, e := Scan(root, Options{MaxDepth: 3, MaxEntries: 2})
	if e != nil {
		t.Fatal(e)
	}
	if !limited.Truncated || len(limited.Entries) != 2 {
		t.Fatalf("truncation: %+v", limited)
	}
}
func TestSymlinkNotFollowed(t *testing.T) {
	root := t.TempDir()
	external := t.TempDir()
	file(t, filepath.Join(external, "secret.txt"))
	if e := os.Symlink(external, filepath.Join(root, "external")); e != nil {
		t.Skipf("no symlinks: %v", e)
	}
	r, e := Scan(root, Options{MaxDepth: 5, MaxEntries: 100})
	if e != nil {
		t.Fatal(e)
	}
	if len(r.Entries) != 1 || r.Entries[0].Kind != "symlink" {
		t.Fatalf("followed symlink: %+v", r)
	}
}
func TestHiddenAndDependencyDirectories(t *testing.T) {
	root := t.TempDir()
	mkdir(t, filepath.Join(root, "node_modules"))
	file(t, filepath.Join(root, "node_modules", "secret"))
	file(t, filepath.Join(root, ".env"))
	file(t, filepath.Join(root, "main.go"))
	r, e := Scan(root, Options{MaxDepth: 3, MaxEntries: 50})
	if e != nil {
		t.Fatal(e)
	}
	for _, ent := range r.Entries {
		if strings.Contains(ent.Path, "secret") || strings.Contains(ent.Path, ".env") {
			t.Fatalf("not filtered: %+v", ent)
		}
	}
	if len(r.Entries) != 2 {
		t.Fatalf("entries: %+v", r.Entries)
	}
	r, e = Scan(root, Options{MaxDepth: 3, MaxEntries: 50, ShowHidden: true})
	if e != nil {
		t.Fatal(e)
	}
	found := false
	for _, ent := range r.Entries {
		if ent.Path == ".env" {
			found = true
		}
	}
	if !found {
		t.Fatal("hidden option ignored")
	}
}
func TestInvalidOptions(t *testing.T) {
	_, e := Scan(t.TempDir(), Options{MaxDepth: 21, MaxEntries: 50})
	if e == nil {
		t.Fatal("missing max depth rejection")
	}
	_, e = Scan(t.TempDir(), Options{MaxDepth: 3, MaxEntries: 10001})
	if e == nil {
		t.Fatal("missing max entries rejection")
	}
}
func TestRootSymlinkRejected(t *testing.T) {
	root := t.TempDir()
	alias := filepath.Join(t.TempDir(), "alias")
	if e := os.Symlink(root, alias); e != nil {
		t.Skipf("no symlinks: %v", e)
	}
	_, e := Scan(alias, Options{MaxDepth: 3, MaxEntries: 100})
	if e == nil {
		t.Fatal("symlink root accepted")
	}
}
