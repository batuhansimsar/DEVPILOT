package tree

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func mk(t *testing.T, root, path string, dir bool) {
	t.Helper()
	p := filepath.Join(root, path)
	if dir {
		if e := os.MkdirAll(p, 0755); e != nil {
			t.Fatal(e)
		}
	} else {
		if e := os.MkdirAll(filepath.Dir(p), 0755); e != nil {
			t.Fatal(e)
		}
		if e := os.WriteFile(p, []byte("fixture"), 0644); e != nil {
			t.Fatal(e)
		}
	}
}
func TestTreeCorrectnessAndRedaction(t *testing.T) {
	root := t.TempDir()
	mk(t, root, "README.md", false)
	mk(t, root, "cmd/main.go", false)
	mk(t, root, "cmd/nested/app.go", false)
	mk(t, root, ".env", false)
	mk(t, root, ".env.local", false)
	mk(t, root, "node_modules/pkg/index.js", false)
	mk(t, root, ".git/HEAD", false)
	outside := t.TempDir()
	mk(t, outside, "secret.txt", false)
	if e := os.Symlink(outside, filepath.Join(root, "out-link")); e != nil {
		t.Skip(e)
	}
	r, e := Scan(root, 2)
	if e != nil {
		t.Fatal(e)
	}
	var b bytes.Buffer
	Render(&b, r)
	got := b.String()
	for _, visible := range []string{"README.md", "cmd/", "main.go", "nested/"} {
		if !strings.Contains(got, visible) {
			t.Fatalf("missing %s: %s", visible, got)
		}
	}
	for _, hidden := range []string{".env", "node_modules", "secret.txt", "app.go", ".git"} {
		if strings.Contains(got, hidden) {
			t.Fatalf("leaked %s: %s", hidden, got)
		}
	}
}
func TestDepthAndOrdering(t *testing.T) {
	root := t.TempDir()
	mk(t, root, "b.txt", false)
	mk(t, root, "a.txt", false)
	mk(t, root, "x/y/z.txt", false)
	r, e := Scan(root, 0)
	if e != nil || len(r.Entries) != 0 {
		t.Fatalf("depth zero: %+v, %v", r, e)
	}
	r, e = Scan(root, 1)
	if e != nil || len(r.Entries) != 3 {
		t.Fatalf("depth one: %+v, %v", r, e)
	}
	if r.Entries[0].Path != "a.txt" || r.Entries[1].Path != "b.txt" {
		t.Fatalf("not sorted: %+v", r.Entries)
	}
}
func TestJSONAndErrors(t *testing.T) {
	root := t.TempDir()
	mk(t, root, "README.md", false)
	var out, stderr bytes.Buffer
	if code := Run([]string{"--json", "--depth", "3", root}, &out, &stderr); code != 0 {
		t.Fatalf("code=%d stderr=%s", code, stderr.String())
	}
	var r Report
	if err := json.Unmarshal(out.Bytes(), &r); err != nil || len(r.Entries) != 1 {
		t.Fatalf("JSON %+v %v", r, err)
	}
	if code := Run([]string{"--depth", "13", root}, &out, &stderr); code != 2 {
		t.Fatal("accepted invalid depth")
	}
	if _, err := Scan(filepath.Join(root, "README.md"), 3); err == nil {
		t.Fatal("accepted file as root")
	}
}
