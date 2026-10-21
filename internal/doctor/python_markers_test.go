package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestHasPythonProjectMarker(t *testing.T) {
	cases := []struct {
		name string
		file string
		want bool
	}{
		{"requirements", "requirements.txt", true},
		{"pyproject", "pyproject.toml", true},
		{"pytest", "pytest.ini", true},
		{"pipfile", "Pipfile", true},
		{"pipenv lock", "Pipfile.lock", true},
		{"uv lock", "uv.lock", true},
		{"poetry lock", "poetry.lock", true},
		{"pdm lock", "pdm.lock", true},
		{"conda yaml", "environment.yml", true},
		{"conda long yaml", "environment.yaml", true},
		{"similarly named lockfile", "uv.lock.backup", false},
		{"unrelated file", "package.json", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			if err := os.WriteFile(filepath.Join(root, tc.file), []byte(""), 0600); err != nil {
				t.Fatal(err)
			}
			if got := hasPythonProjectMarker(root); got != tc.want {
				t.Fatalf("got %v, want %v", got, tc.want)
			}
		})
	}
}

func TestHasPythonProjectMarkerRejectsDirectory(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "Pipfile"), 0700); err != nil {
		t.Fatal(err)
	}
	if hasPythonProjectMarker(root) {
		t.Fatal("directory must not count as Python project")
	}
}

func TestHasPythonProjectMarkerRejectsSymlink(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "target")
	if err := os.WriteFile(target, nil, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, filepath.Join(root, "Pipfile")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	if hasPythonProjectMarker(root) {
		t.Fatal("symlink must not count as Python project")
	}
}
