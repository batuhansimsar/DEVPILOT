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
