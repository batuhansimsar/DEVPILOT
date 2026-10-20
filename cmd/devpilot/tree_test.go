package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/batuhansimsar/DEVPILOT/internal/projecttree"
)

func TestTreeCommandJSONEndToEnd(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "src"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "src", "main.go"), []byte("package main\n"), 0644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	code := run(context.Background(), []string{"tree", "--json", "--depth=2", root}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("tree returned %d: %s", code, stderr.String())
	}
	var result projecttree.Result
	if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if len(result.Entries) != 2 || result.Entries[1].Path != "src/main.go" {
		t.Fatalf("unexpected entries: %+v", result.Entries)
	}
}

func TestTreeCommandRejectsInvalidDepth(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := run(context.Background(), []string{"tree", "--depth=9"}, &stdout, &stderr)
	if code != 2 {
		t.Fatalf("expected usage error 2, got %d (%s)", code, stderr.String())
	}
}
