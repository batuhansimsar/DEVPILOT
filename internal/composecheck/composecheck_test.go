package composecheck

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func write(t *testing.T, dir, name string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, name), []byte("services:\n  app:\n    image: busybox"), 0600); err != nil {
		t.Fatal(err)
	}
}
func code(fs []Finding, c string) bool {
	for _, f := range fs {
		if f.Code == c {
			return true
		}
	}
	return false
}
func missingDocker(string) (string, error)   { return "", errors.New("not installed") }
func installedDocker(string) (string, error) { return "/usr/bin/docker", nil }

func TestComposeMissingDockerReportsWarning(t *testing.T) {
	root := t.TempDir()
	write(t, root, "compose.yaml")
	result := Inspect(root, missingDocker)
	if !code(result, "docker-compose-found") || !code(result, "docker-cli-missing") {
		t.Fatalf("findings: %+v", result)
	}
	if code(result, "dockerignore-not-found") {
		t.Fatal("no Dockerfile; no dockerignore suggestion")
	}
}
func TestMultipleComposeFilesNoContentRead(t *testing.T) {
	root := t.TempDir()
	write(t, root, "compose.yml")
	write(t, root, "docker-compose.yaml")
	got := Inspect(root, installedDocker)
	if !code(got, "docker-compose-multiple-files") || !code(got, "docker-cli-found") {
		t.Fatalf("findings: %+v", got)
	}
	for _, f := range got {
		if strings.Contains(f.Message, "busybox") {
			t.Fatal("included file contents")
		}
	}
}
func TestDockerfileSuggestsDockerignore(t *testing.T) {
	root := t.TempDir()
	write(t, root, "Dockerfile")
	if !code(Inspect(root, missingDocker), "dockerignore-not-found") {
		t.Fatal("missing .dockerignore suggestion")
	}
	write(t, root, ".dockerignore")
	if code(Inspect(root, missingDocker), "dockerignore-not-found") {
		t.Fatal(".dockerignore exists")
	}
}
func TestSymlinkedComposeIgnored(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(t.TempDir(), "compose.yaml")
	if err := os.WriteFile(target, []byte("services: {}"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, filepath.Join(root, "compose.yaml")); err != nil {
		t.Skipf("symlink unavailable: %v", err)
	}
	if got := Inspect(root, missingDocker); len(got) != 0 {
		t.Fatalf("symlink followed: %+v", got)
	}
}
func TestOrdinaryProjectNoWarnings(t *testing.T) {
	if got := Inspect(t.TempDir(), missingDocker); len(got) != 0 {
		t.Fatalf("unexpected %+v", got)
	}
}
