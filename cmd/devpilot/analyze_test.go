package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestAnalyzeCommandJSON(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "main.go"), []byte("package main"), 0600); err != nil {
		t.Fatal(err)
	}
	var out, errs bytes.Buffer
	if code := analyzeCommand([]string{"--json", dir}, &out, &errs); code != 0 {
		t.Fatalf("exit=%d stderr=%s", code, errs.String())
	}
	var doc struct {
		FileCount int `json:"file_count"`
	}
	if err := json.Unmarshal(out.Bytes(), &doc); err != nil {
		t.Fatal(err)
	}
	if doc.FileCount != 1 {
		t.Fatalf("files=%d", doc.FileCount)
	}
}
func TestAnalyzeCommandInvalidArgs(t *testing.T) {
	var out, errs bytes.Buffer
	if code := analyzeCommand([]string{"a", "b"}, &out, &errs); code != 2 {
		t.Fatal(code)
	}
}
