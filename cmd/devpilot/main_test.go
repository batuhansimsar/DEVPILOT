package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDoctorJSON(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module test\ngo 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	var out, errOut bytes.Buffer
	status := run(context.Background(), []string{"doctor", "--json", dir}, &out, &errOut)
	if status != 0 {
		t.Fatalf("status=%d stderr=%s", status, errOut.String())
	}
	var doc map[string]any
	if err := json.Unmarshal(out.Bytes(), &doc); err != nil {
		t.Fatal(err)
	}
	if doc["path"] != dir {
		t.Fatalf("path %v", doc["path"])
	}
}
func TestUntrustedTestNeverRuns(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module test\ngo 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	var out, errOut bytes.Buffer
	status := run(context.Background(), []string{"test", dir}, &out, &errOut)
	if status != 2 || !strings.Contains(errOut.String(), "Refusing") {
		t.Fatalf("status=%d output=%s", status, errOut.String())
	}
}
func TestBadTimeout(t *testing.T) {
	var out, errOut bytes.Buffer
	if status := run(context.Background(), []string{"test", "--trust", "--timeout=11m"}, &out, &errOut); status != 2 {
		t.Fatal(status)
	}
}

func TestTreeJSONAndValidation(t *testing.T) {
	dir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir, "src"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "src", "main.go"), []byte("package main"), 0600); err != nil {
		t.Fatal(err)
	}
	var out, errOut bytes.Buffer
	status := run(context.Background(), []string{"tree", "--json", "--depth=2", dir}, &out, &errOut)
	if status != 0 {
		t.Fatalf("status=%d stderr=%s", status, errOut.String())
	}
	var result struct {
		Entries []struct {
			Path string `json:"path"`
		} `json:"entries"`
	}
	if err := json.Unmarshal(out.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if len(result.Entries) != 2 || result.Entries[0].Path != "src" || result.Entries[1].Path != "src/main.go" {
		t.Fatalf("unexpected entries: %+v", result.Entries)
	}
	out.Reset()
	errOut.Reset()
	if code := run(context.Background(), []string{"tree", "--depth=0", dir}, &out, &errOut); code != 2 {
		t.Fatalf("bad depth should fail: %d", code)
	}
}
