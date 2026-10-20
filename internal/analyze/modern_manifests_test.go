package analyze

import (
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
)

func TestInspectRecognizesModernWorkspaceManifests(t *testing.T) {
	root := t.TempDir()
	cases := []struct {
		path      string
		ecosystem string
	}{
		{"go.work", "Go"},
		{"sub/Pipfile.lock", "Python"},
		{"sub/deno.jsonc", "Deno"},
		{"js/bun.lock", "Bun"},
		{"js/bun.lockb", "Bun"},
	}
	var want []string
	for _, tc := range cases {
		file := filepath.Join(root, filepath.FromSlash(tc.path))
		if err := os.MkdirAll(filepath.Dir(file), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(file, []byte("test fixture"), 0600); err != nil {
			t.Fatal(err)
		}
		want = append(want, tc.path+" ("+tc.ecosystem+")")
	}
	// Files that resemble manifests must not be misidentified.
	for _, name := range []string{"go.work.bak", "deno.jsonc.old", "bun.lock.tmp"} {
		if err := os.WriteFile(filepath.Join(root, name), []byte("ignored"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	// Inspect returns manifest paths in lexicographic order.
	sort.Strings(want)
	if !reflect.DeepEqual(report.Manifests, want) {
		t.Fatalf("manifests = %q; want %q", report.Manifests, want)
	}
}
