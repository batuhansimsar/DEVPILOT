package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestCIAuditCommandWired(t *testing.T) {
	root := t.TempDir()
	folder := filepath.Join(root, ".github", "workflows")
	if err := os.MkdirAll(folder, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(folder, "main.yml"), []byte("steps:\n  - uses: actions/checkout@v4\n"), 0644); err != nil {
		t.Fatal(err)
	}
	var out, errOut bytes.Buffer
	code := run(context.Background(), []string{"ci-audit", "--json", root}, &out, &errOut)
	if code != 1 {
		t.Fatalf("expected audit warning status: got=%d err=%s", code, errOut.String())
	}
	var result struct {
		Findings []any `json:"findings"`
	}
	if err := json.Unmarshal(out.Bytes(), &result); err != nil {
		t.Fatalf("bad JSON: %v", err)
	}
	if len(result.Findings) != 1 {
		t.Fatalf("expected evidence: %s", out.String())
	}
}
