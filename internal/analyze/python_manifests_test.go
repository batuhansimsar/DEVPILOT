package analyze

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"testing"
)

func TestInspectPythonLockfileManifests(t *testing.T) {
	root := t.TempDir()
	files := []string{
		"uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock",
		"services/api/uv.lock", "services/api/poetry.lock",
	}
	for _, name := range files {
		path := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte("not parsed"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	for _, name := range []string{"uv.lock.bak", "uv.lock.old", "Poetry.lock", "pdm.lock.tmp"} {
		if err := os.WriteFile(filepath.Join(root, name), []byte("noise"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	if runtime.GOOS != "windows" {
		if err := os.MkdirAll(filepath.Join(root, "link"), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.Symlink(filepath.Join(root, "uv.lock"), filepath.Join(root, "link", "uv.lock")); err != nil {
			t.Fatal(err)
		}
	}
	want := []string{
		"Pipfile.lock (Python)", "pdm.lock (Python)", "poetry.lock (Python)",
		"services/api/poetry.lock (Python)", "services/api/uv.lock (Python)", "uv.lock (Python)",
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(report.Manifests, want) {
		t.Fatalf("manifests = %q, want %q", report.Manifests, want)
	}
}
