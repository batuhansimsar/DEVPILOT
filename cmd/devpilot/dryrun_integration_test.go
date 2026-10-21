package main

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDryRunWithoutTrustOrInstalledTool(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module test\ngo 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", "") // Preview must not require the executable to be installed.
	var out, errOut bytes.Buffer
	status := run(context.Background(), []string{"test", "--dry-run", dir}, &out, &errOut)
	if status != 0 || !strings.Contains(out.String(), "Dry run: no command executed.") ||
		!strings.Contains(out.String(), `Executable: "go"`) ||
		!strings.Contains(out.String(), `  "./..."`) {
		t.Fatalf("status=%d stdout=%q stderr=%q", status, out.String(), errOut.String())
	}
}

func TestDryRunWithTrustRejectsConflictingFlags(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module test\ngo 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", "")
	var out, errOut bytes.Buffer
	status := run(context.Background(), []string{"test", "--trust", "--dry-run", dir}, &out, &errOut)
	if status != 2 || out.Len() != 0 || !strings.Contains(errOut.String(), "cannot be combined") {
		t.Fatalf("status=%d stdout=%q stderr=%q", status, out.String(), errOut.String())
	}
}

func TestDryRunWithoutDetectedCommand(t *testing.T) {
	var out, errOut bytes.Buffer
	status := run(context.Background(), []string{"test", "--dry-run", t.TempDir()}, &out, &errOut)
	if status != 2 || !strings.Contains(errOut.String(), "No supported test command discovered.") {
		t.Fatalf("status=%d stdout=%q stderr=%q", status, out.String(), errOut.String())
	}
}
