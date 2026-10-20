package main

import (
    "bytes"
    "context"
    "os"
    "path/filepath"
    "strings"
    "testing"
)

func TestDockerfileCommandJSON(t *testing.T) {
    root := t.TempDir()
    if err := os.WriteFile(filepath.Join(root, "Dockerfile"), []byte("FROM alpine:latest\nCOPY . .\n"), 0644); err != nil { t.Fatal(err) }
    var out, stderr bytes.Buffer
    exit := run(context.Background(), []string{"dockerfile", "--json", root}, &out, &stderr)
    if exit != 1 { t.Fatalf("expected warnings, got %d: %s", exit, stderr.String()) }
    if !strings.Contains(out.String(), `"mutable-base-image"`) { t.Fatalf("missing JSON evidence: %s", out.String()) }
}
func TestDockerfileCommandMissingFile(t *testing.T) {
    var out, stderr bytes.Buffer
    exit := run(context.Background(), []string{"dockerfile", t.TempDir()}, &out, &stderr)
    if exit != 2 || !strings.Contains(stderr.String(), "Dockerfile") { t.Fatalf("unexpected error handling: %d %s", exit, stderr.String()) }
}
