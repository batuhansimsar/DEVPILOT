package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestAnalyzeCommandQuotesUntrustedPaths(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Windows does not allow escape characters in file names")
	}
	root := filepath.Join(t.TempDir(), "workspace\x1b[2J\n")
	if err := os.MkdirAll(filepath.Join(root, ".github", "workflows"), 0700); err != nil {
		t.Fatal(err)
	}
	const dockerfile = "Dockerfile.\x1b[2J"
	const workflow = "build\x1b[2J\n.yml"
	for _, path := range []string{dockerfile, filepath.Join(".github", "workflows", workflow)} {
		if err := os.WriteFile(filepath.Join(root, path), []byte("test"), 0600); err != nil {
			t.Fatal(err)
		}
	}

	var out, errs bytes.Buffer
	if code := analyzeCommand([]string{root}, &out, &errs); code != 0 {
		t.Fatalf("exit=%d stderr=%q", code, errs.String())
	}
	text := out.String()
	if strings.ContainsRune(text, '\x1b') || strings.Count(text, "\n") != 5 {
		t.Fatalf("control characters or injected lines in output: %q", text)
	}
	for _, want := range []string{
		quoteTerminalPath(root),
		quoteTerminalPath(dockerfile + " (Docker)"),
		quoteTerminalPath(filepath.ToSlash(filepath.Join(".github", "workflows", workflow))),
	} {
		if !strings.Contains(text, want) {
			t.Fatalf("missing escaped value %s: %q", want, text)
		}
	}
	out.Reset()
	errs.Reset()
	if code := analyzeCommand([]string{"--json", root}, &out, &errs); code != 0 {
		t.Fatalf("JSON exit=%d stderr=%q", code, errs.String())
	}
	var report struct {
		Path string   `json:"path"`
		CI   []string `json:"ci"`
	}
	if err := json.Unmarshal(out.Bytes(), &report); err != nil {
		t.Fatal(err)
	}
	if report.Path != root || len(report.CI) != 1 || !strings.Contains(report.CI[0], workflow) {
		t.Fatalf("JSON path values unexpectedly modified: %+v", report)
	}
}

func TestAnalyzeCommandRedactsPathErrors(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Windows does not allow escape characters in file names")
	}
	path := filepath.Join(t.TempDir(), "nonexistent\x1b[2J\n")
	var out, errs bytes.Buffer
	if code := analyzeCommand([]string{path}, &out, &errs); code != 2 {
		t.Fatalf("exit=%d stderr=%q", code, errs.String())
	}
	diagnostic := errs.String()
	if !strings.Contains(diagnostic, "file does not exist") {
		t.Fatalf("expected actionable error class, got %q", diagnostic)
	}
	for _, untrusted := range []string{path, "nonexistent", "\\x1b", "\x1b", "\\n"} {
		if strings.Contains(diagnostic, untrusted) {
			t.Fatalf("path details or terminal escapes leaked in diagnostic: %q", diagnostic)
		}
	}
	if strings.Count(diagnostic, "\n") != 1 {
		t.Fatalf("unexpected terminal line injection: %q", diagnostic)
	}
}
