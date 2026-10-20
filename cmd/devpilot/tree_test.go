package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestTreeJSONAndRedaction(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "main.go"), []byte("package main"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, ".env.local"), []byte("SECRET=value"), 0600); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	code := run(context.Background(), []string{"tree", "--json", dir}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("exit=%d stderr=%s", code, stderr.String())
	}
	var data struct {
		Entries []struct{ Path string `json:"path"` } `json:"entries"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &data); err != nil {
		t.Fatal(err)
	}
	if len(data.Entries) != 1 || data.Entries[0].Path != "main.go" {
		t.Fatalf("unexpected entries: %+v", data.Entries)
	}
}

func TestTreeInvalidBounds(t *testing.T) {
	var out, errOut bytes.Buffer
	if code := run(context.Background(), []string{"tree", "--depth", "100"}, &out, &errOut); code != 2 {
		t.Fatalf("expected usage error, got %d", code)
	}
}
