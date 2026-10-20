package analyze

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"testing"
)

func TestDotnetManifestExtensions(t *testing.T) {
	for _, name := range []string{"App.csproj", "App.fsproj", "App.vbproj", "Solution.sln", "Solution.slnx", "APP.CSPROJ", "SOLUTION.SLNX"} {
		if !isDotnetManifest(name) {
			t.Errorf("missed .NET manifest %q", name)
		}
	}
	for _, name := range []string{"NotSolution.slnx.bak", "app.cs", "project.json", "fakecsproj", "hello.slnx.txt"} {
		if isDotnetManifest(name) {
			t.Errorf("incorrectly classified %q as a .NET manifest", name)
		}
	}
}

func TestAnalyzeDotnetWorkspaceManifests(t *testing.T) {
	root := t.TempDir()
	for _, name := range []string{"Backend/App.csproj", "Backend/Tests.fsproj", "Tools/Worker.vbproj", "Solution.slnx", "Legacy.sln", "UPPER.CSPROJ"} {
		path := filepath.Join(root, name)
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(""), 0600); err != nil {
			t.Fatal(err)
		}
	}
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"Backend/App.csproj (.NET)", "Backend/Tests.fsproj (.NET)", "Legacy.sln (.NET)", "Solution.slnx (.NET)", "Tools/Worker.vbproj (.NET)", "UPPER.CSPROJ (.NET)"}
	if !reflect.DeepEqual(r.Manifests, want) {
		t.Fatalf("manifests=%v; want %v", r.Manifests, want)
	}
	if r.FileCount != len(want) {
		t.Fatalf("file_count=%d", r.FileCount)
	}
}

func TestAnalyzeIgnoresSymlinkedDotnetManifest(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlinks require privileges on Windows")
	}
	root := t.TempDir()
	outside := filepath.Join(t.TempDir(), "Secrets.csproj")
	if err := os.WriteFile(outside, []byte("not to be read"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "Secret.csproj")); err != nil {
		t.Fatal(err)
	}
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Manifests) != 0 || r.FileCount != 0 {
		t.Fatalf("symlink followed: %+v", r)
	}
}
