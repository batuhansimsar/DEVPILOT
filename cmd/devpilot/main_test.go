package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestJSONDoctor(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/app\n\ngo 1.23\n"), 0644); err != nil {
		t.Fatal(err)
	}
	var out, stderr bytes.Buffer
	exit := run([]string{"doctor", "--path", root, "--json"}, &out, &stderr)
	if exit != 0 {
		t.Fatalf("exit %d stderr=%s", exit, stderr.String())
	}
	var parsed struct {
		SchemaVersion int   `json:"schema_version"`
		TestCommands  []any `json:"test_commands"`
	}
	if err := json.Unmarshal(out.Bytes(), &parsed); err != nil {
		t.Fatalf("invalid json: %v: %s", err, out.String())
	}
	if parsed.SchemaVersion != 1 || len(parsed.TestCommands) != 1 {
		t.Errorf("unexpected JSON report: %s", out.String())
	}
}

func TestInvalidFlags(t *testing.T) {
	var out, err bytes.Buffer
	if status := run([]string{"doctor", "--run-tests"}, &out, &err); status != 2 {
		t.Fatalf("expected permission error, got %d", status)
	}
	if status := run([]string{"doctor", "--timeout=-1s"}, &out, &err); status != 2 {
		t.Fatalf("expected invalid timeout, got %d", status)
	}
}
