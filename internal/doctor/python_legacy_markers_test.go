package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLegacyPythonMarkers(t *testing.T) {
	for _, name := range []string{"setup.py", "setup.cfg"} {
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			if err := os.WriteFile(filepath.Join(root, name), []byte("untrusted project metadata"), 0600); err != nil {
				t.Fatal(err)
			}
			if !hasPythonProjectMarker(root) {
				t.Fatalf("%s should identify a Python project", name)
			}
		})
	}
}

func TestLegacyPythonMarkersRejectUnsafeFileTypes(t *testing.T) {
	for _, name := range []string{"setup.py", "setup.cfg"} {
		t.Run(name+" directory", func(t *testing.T) {
			root := t.TempDir()
			if err := os.Mkdir(filepath.Join(root, name), 0700); err != nil {
				t.Fatal(err)
			}
			if hasPythonProjectMarker(root) {
				t.Fatal("directory must not be treated as Python project metadata")
			}
		})
		t.Run(name+" symlink", func(t *testing.T) {
			root := t.TempDir()
			target := filepath.Join(t.TempDir(), "outside")
			if err := os.WriteFile(target, []byte("outside"), 0600); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(target, filepath.Join(root, name)); err != nil {
				t.Skipf("symlink unsupported: %v", err)
			}
			if hasPythonProjectMarker(root) {
				t.Fatal("symlink must not be treated as Python project metadata")
			}
		})
	}
}

func TestLegacyPythonInspect(t *testing.T) {
	for _, name := range []string{"setup.py", "setup.cfg"} {
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			if err := os.WriteFile(filepath.Join(root, name), []byte("untrusted project metadata"), 0600); err != nil {
				t.Fatal(err)
			}
			report, err := Inspect(root)
			if err != nil {
				t.Fatal(err)
			}
			if len(report.Languages) != 1 || report.Languages[0] != "Python" {
				t.Fatalf("language detection: %v", report.Languages)
			}
			if report.Tests != nil {
				t.Fatalf("legacy packaging alone must not imply a safe test command: %+v", report.Tests)
			}
		})
	}
}
