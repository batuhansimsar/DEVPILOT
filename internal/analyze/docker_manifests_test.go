package analyze

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"testing"
)

func TestDockerManifestKind(t *testing.T) {
	cases := []struct {
		name string
		kind string
	}{
		{"Dockerfile", "Docker"},
		{"Dockerfile.dev", "Docker"},
		{"compose.yaml", "Docker Compose"},
		{"compose.yml", "Docker Compose"},
		{"docker-compose.yaml", "Docker Compose"},
		{"docker-compose.yml", "Docker Compose"},
		{"docker-compose.override.yml", "Docker Compose"},
		{"compose.dev.yaml", "Docker Compose"},
		{"Dockerfile-not-real", ""},
		{"library.fsproj.backup", ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			kind, ok := dockerManifestKind(tc.name)
			if kind != tc.kind || ok != (tc.kind != "") {
				t.Fatalf("dockerManifestKind(%q) = (%q, %v); want (%q, %v)", tc.name, kind, ok, tc.kind, tc.kind != "")
			}
		})
	}
}

func TestInspectDetectsNestedDockerAndDotnetManifests(t *testing.T) {
	root := t.TempDir()
	for _, path := range []string{
		"Dockerfile", "services/api/Dockerfile.dev", "services/api/compose.yaml",
		"services/api/App.csproj", "services/api/App.slnx", "services/api/Ignore.fsproj.backup",
	} {
		full := filepath.Join(root, filepath.FromSlash(path))
		if err := os.MkdirAll(filepath.Dir(full), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(full, []byte("fixture"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.MkdirAll(filepath.Join(root, "node_modules"), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "node_modules", "Dockerfile"), []byte("ignored"), 0600); err != nil {
		t.Fatal(err)
	}
	if runtime.GOOS != "windows" {
		outside := filepath.Join(t.TempDir(), "compose.yml")
		if err := os.WriteFile(outside, []byte("secret"), 0600); err != nil {
			t.Fatal(err)
		}
		if err := os.Symlink(outside, filepath.Join(root, "compose.yml")); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	want := []string{
		"Dockerfile (Docker)",
		"services/api/App.csproj (.NET)",
		"services/api/App.slnx (.NET)",
		"services/api/Dockerfile.dev (Docker)",
		"services/api/compose.yaml (Docker Compose)",
	}
	if !reflect.DeepEqual(report.Manifests, want) {
		t.Fatalf("manifests = %q, want %q", report.Manifests, want)
	}
	if report.FileCount != 6 {
		t.Fatalf("file count = %d, want 6", report.FileCount)
	}
}
