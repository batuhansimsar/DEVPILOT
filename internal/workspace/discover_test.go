package workspace

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"testing"
)

func write(t *testing.T, root, rel string) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(rel))
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte("{}"), 0600); err != nil {
		t.Fatal(err)
	}
}

func TestDiscoverNestedProjectsAndIgnoreDependencies(t *testing.T) {
	root := t.TempDir()
	write(t, root, "go.mod")
	write(t, root, "apps/web/package.json")
	write(t, root, "apps/web/tsconfig.json")
	write(t, root, "apps/api/go.mod")
	write(t, root, "apps/api/package.json")
	write(t, root, "node_modules/bad/package.json")
	write(t, root, "apps/web/dist/build/package.json")
	write(t, root, "apps/deep/one/two/three/package.json") // depth 5, outside limit
	got, err := Discover(root)
	if err != nil {
		t.Fatal(err)
	}
	if got.Truncated {
		t.Fatal("unexpected truncation")
	}
	paths := []string{}
	for _, project := range got.Projects {
		paths = append(paths, project.Path)
	}
	if !reflect.DeepEqual(paths, []string{".", "apps/api", "apps/web"}) {
		t.Fatalf("projects: %+v", got.Projects)
	}
	if !reflect.DeepEqual(got.Projects[1].Markers, []string{"go.mod", "package.json"}) {
		t.Fatalf("markers: %+v", got.Projects[1].Markers)
	}
}

func TestDiscoverSkipsSymlinkAndRejectsFile(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	write(t, outside, "package.json")
	if runtime.GOOS != "windows" {
		if err := os.Symlink(outside, filepath.Join(root, "external")); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Discover(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(report.Projects) != 0 {
		t.Fatalf("followed an outside path: %+v", report)
	}
	if runtime.GOOS != "windows" && report.SkippedSymlinks != 1 {
		t.Fatalf("symlinks: %d", report.SkippedSymlinks)
	}
	write(t, root, "file.txt")
	if _, err := Discover(filepath.Join(root, "file.txt")); err == nil {
		t.Fatal("expected non-directory error")
	}
}

func TestDiscoverIsDeterministic(t *testing.T) {
	root := t.TempDir()
	write(t, root, "b/package.json")
	write(t, root, "a/go.mod")
	one, err := Discover(root)
	if err != nil {
		t.Fatal(err)
	}
	two, err := Discover(root)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(one, two) {
		t.Fatalf("different results: %+v vs %+v", one, two)
	}
}

func TestProjectMarker(t *testing.T) {
	for _, name := range []string{"go.mod", "Cargo.toml", "app.csproj", "pyproject.toml", "pytest.ini", "package.json"} {
		if !projectMarker(name) {
			t.Errorf("missing %s", name)
		}
	}
	for _, name := range []string{"README.md", "package-lock.json", ".csproj", "notpackage.json"} {
		if projectMarker(name) {
			t.Errorf("false positive %s", name)
		}
	}
}
