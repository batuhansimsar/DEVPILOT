package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDoctorJSON(t *testing.T) {
	root := t.TempDir()
	if e := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.org/test\n\ngo 1.23\n"), 0644); e != nil {
		t.Fatal(e)
	}
	var out, errBuf bytes.Buffer
	code := run([]string{"doctor", "--path", root, "--json"}, &out, &errBuf)
	if code != 0 {
		t.Fatalf("exit %d: %s", code, errBuf.String())
	}
	var report map[string]any
	if e := json.Unmarshal(out.Bytes(), &report); e != nil {
		t.Fatal(e)
	}
	if len(report["tests"].([]any)) != 1 {
		t.Fatalf("bad json report: %s", out.String())
	}
}
func TestTestCommandDoesNotExecuteWithoutTrust(t *testing.T) {
	root := t.TempDir()
	if e := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.org/test\n\ngo 1.23\n"), 0644); e != nil {
		t.Fatal(e)
	}
	var out, errBuf bytes.Buffer
	code := run([]string{"test", "--path", root, "--run", "go:."}, &out, &errBuf)
	if code != 2 || !strings.Contains(errBuf.String(), "--trust") {
		t.Fatalf("expected denial, got %d %s", code, errBuf.String())
	}
}
func TestUnknownCommand(t *testing.T) {
	var out, errBuf bytes.Buffer
	code := run([]string{"erase-everything"}, &out, &errBuf)
	if code != 2 || !strings.Contains(errBuf.String(), "Unknown command") {
		t.Fatalf("exit=%d message=%s", code, errBuf.String())
	}
}
