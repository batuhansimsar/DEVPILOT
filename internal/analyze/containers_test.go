package analyze

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
)

func TestContainerFileRecognition(t *testing.T) {
	cases := map[string]bool{
		"Dockerfile": true, "Dockerfile.prod": true, "api.Dockerfile": true,
		"Containerfile": true, "Containerfile.dev": true, "api.Containerfile": true,
		"compose.yml": true, "compose.yaml": true,
		"docker-compose.yml": true, "docker-compose.yaml": true,
		"api.compose.yaml": true, "api.compose.yml": true,
		"Dockerfile.": false, "Containerfile.": false, ".compose.yml": false,
		"Dockerfile.txt.bak": false, "not-compose.yml": false,
		"docker-compose.json": false, "DOCKERFILE": false, "plain.txt": false,
	}
	for name, want := range cases {
		if got := isContainerConfig(name); got != want {
			t.Errorf("isContainerConfig(%q)=%t; want %t", name, got, want)
		}
	}
}

func TestInspectContainerConfigurations(t *testing.T) {
	root := t.TempDir()
	paths := []string{
		"Dockerfile", "services/api/Dockerfile.dev", "services/web/Containerfile",
		"infra/compose.yaml", "infra/prod.compose.yml", "docker-compose.yml",
		"node_modules/Dockerfile", "build/docker-compose.yaml", "readme.txt",
	}
	for _, name := range paths {
		path := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte("SECRET_TOKEN=must-not-leak"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	if runtime.GOOS != "windows" {
		outside := filepath.Join(t.TempDir(), "Dockerfile")
		if err := os.WriteFile(outside, []byte("secret"), 0600); err != nil {
			t.Fatal(err)
		}
		if err := os.Symlink(outside, filepath.Join(root, "linked.Dockerfile")); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"Dockerfile", "docker-compose.yml", "infra/compose.yaml", "infra/prod.compose.yml", "services/api/Dockerfile.dev", "services/web/Containerfile"}
	if !reflect.DeepEqual(report.Containers, want) {
		t.Fatalf("containers=%v, want %v", report.Containers, want)
	}
	b, err := json.Marshal(report)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(b), "SECRET_TOKEN") || !strings.Contains(string(b), "\"containers\"") {
		t.Fatalf("unexpected report JSON: %s", b)
	}
	if report.FileCount != len(paths)-2 {
		t.Fatalf("files=%d", report.FileCount)
	}
}
