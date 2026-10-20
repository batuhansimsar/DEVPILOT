package main

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestPortableDiagnosticReport(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module example.com/test\ngo 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	var out, errOut bytes.Buffer
	status := run(context.Background(), []string{"report", dir}, &out, &errOut)
	if status != 0 {
		t.Fatalf("status=%d stderr=%s", status, errOut.String())
	}
	result := out.String()
	if strings.Contains(result, dir) {
		t.Fatal("absolute workspace path disclosed")
	}
	if !strings.Contains(result, "# DevPilot diagnostic snapshot") || !strings.Contains(result, "Go") {
		t.Fatal("report missing expected project information")
	}
}

func TestPortableReportRejectsExtraArgs(t *testing.T) {
	var out, errOut bytes.Buffer
	if status := run(context.Background(), []string{"report", ".", "."}, &out, &errOut); status != 2 {
		t.Fatalf("expected input error, got %d", status)
	}
}
