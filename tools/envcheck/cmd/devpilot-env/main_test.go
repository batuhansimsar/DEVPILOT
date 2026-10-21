package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/batuhansimsar/DEVPILOT/tools/envcheck/internal/envcheck"
)

func TestCLIOutputAndExitCodes(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".env.example"), []byte("SOME_UNCONFIGURED_KEY_42=\n"), 0600); err != nil {
		t.Fatal(err)
	}
	var out, stderr bytes.Buffer
	code := run([]string{"--path", root, "--strict", "--json"}, &out, &stderr)
	if code != 1 || stderr.Len() != 0 {
		t.Fatalf("unexpected code=%d stderr=%s", code, stderr.String())
	}
	var r envcheck.Report
	if err := json.Unmarshal(out.Bytes(), &r); err != nil {
		t.Fatal(err)
	}
	if r.Summary.Unconfigured != 1 || r.Variables[0].Name != "SOME_UNCONFIGURED_KEY_42" {
		t.Fatalf("unexpected JSON report: %+v", r)
	}
	out.Reset()
	if code := run([]string{"--path", root}, &out, &stderr); code != 0 || !strings.Contains(out.String(), "unconfigured") {
		t.Fatalf("unexpected default output: code=%d out=%s", code, out.String())
	}
}

func TestInvalidFlagReturnsTwo(t *testing.T) {
	var out, stderr bytes.Buffer
	if code := run([]string{"--nonexistent"}, &out, &stderr); code != 2 {
		t.Fatalf("expected exit 2, got %d", code)
	}
}
