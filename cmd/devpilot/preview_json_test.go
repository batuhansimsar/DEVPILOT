package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestJSONDryRunDoesNotExecute(t *testing.T) {
	root := filepath.Join(t.TempDir(), "project with spaces")
	if err := os.Mkdir(root, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/project\ngo 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", t.TempDir()) // runner is not installed; no subprocess should run
	var out, errOut bytes.Buffer
	code := run(context.Background(), []string{"test", "--dry-run", "--json", root}, &out, &errOut)
	if code != 0 || errOut.Len() != 0 {
		t.Fatalf("status=%d stderr=%s", code, errOut.String())
	}
	var report struct {
		WorkingDirectory string   `json:"working_directory"`
		Executable       string   `json:"executable"`
		Arguments        []string `json:"arguments"`
		Executed         bool     `json:"executed"`
	}
	if err := json.Unmarshal(out.Bytes(), &report); err != nil {
		t.Fatal(err)
	}
	if report.WorkingDirectory != root || report.Executable != "go" || strings.Join(report.Arguments, " ") != "test ./..." || report.Executed {
		t.Fatalf("incorrect test plan: %+v", report)
	}
}

func TestJSONPreviewRequiresDryRun(t *testing.T) {
	for _, args := range [][]string{{"test", "--trust", "--json"}, {"test", "--json"}} {
		var out, errOut bytes.Buffer
		code := run(context.Background(), args, &out, &errOut)
		if code != 2 || !strings.Contains(errOut.String(), "--json requires --dry-run") || out.Len() != 0 {
			t.Fatalf("args=%v status=%d stderr=%q", args, code, errOut.String())
		}
	}
}

func TestTrustAndPreviewAreExclusive(t *testing.T) {
	var out, errOut bytes.Buffer
	code := run(context.Background(), []string{"test", "--trust", "--dry-run"}, &out, &errOut)
	if code != 2 || !strings.Contains(errOut.String(), "cannot be combined") {
		t.Fatalf("status=%d stderr=%s", code, errOut.String())
	}
}

type brokenWriter struct{}
func (brokenWriter) Write(p []byte) (int, error) { return 0, errors.New("broken pipe") }

func TestJSONPreviewPreservesArgumentBoundariesAndPropagatesErrors(t *testing.T) {
	var out bytes.Buffer
	if err := printJSONTestPreview(&out, "/work\nname", "go", []string{"test", "\x1b[31m./..."}); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(out.String(), "\x1b") || strings.Contains(out.String(), "/work\nname") {
		t.Fatalf("raw control characters leaked: %q", out.String())
	}
	var decoded map[string]any
	if err := json.Unmarshal(out.Bytes(), &decoded); err != nil {
		t.Fatal(err)
	}
	if decoded["working_directory"] != "/work\nname" || decoded["executed"] != false {
		t.Fatalf("bad JSON: %+v", decoded)
	}
	if err := printJSONTestPreview(brokenWriter{}, "/work", "go", []string{"test"}); err == nil {
		t.Fatal("expected writer error")
	}
}
