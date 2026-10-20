package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestAnalyzeCommandContainerInventory(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "Dockerfile"), []byte("FROM scratch"), 0600); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	if code := analyzeCommand([]string{"--json", root}, &stdout, &stderr); code != 0 {
		t.Fatalf("JSON exit=%d stderr=%s", code, stderr.String())
	}
	var report map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &report); err != nil {
		t.Fatal(err)
	}
	containers, ok := report["containers"].([]any)
	if !ok || len(containers) != 1 || containers[0] != "Dockerfile" {
		t.Fatalf("containers=%v", report["containers"])
	}
	stdout.Reset()
	stderr.Reset()
	if code := analyzeCommand([]string{root}, &stdout, &stderr); code != 0 {
		t.Fatalf("text exit=%d stderr=%s", code, stderr.String())
	}
	if !strings.Contains(stdout.String(), "Container: Dockerfile") {
		t.Fatalf("missing container listing: %q", stdout.String())
	}
}
