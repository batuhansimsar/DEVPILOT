package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestEscapeTerminalText(t *testing.T) {
	for _, tc := range []struct {
		name, input, want string
	}{
		{"plain", "Test discovered: go test ./...", "Test discovered: go test ./..."},
		{"escape", "Project x\x1b[2J", `Project x\x1b[2J`},
		{"newline", "line\nnext", `line\nnext`},
		{"bidi", "ref\u202ereversed", `ref\u202ereversed`},
		{"quotation", `message "quoted"`, `message \"quoted\"`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got := escapeTerminalText(tc.input)
			if got != tc.want || strings.ContainsRune(got, '\x1b') ||
				strings.ContainsRune(got, '\n') || strings.ContainsRune(got, '\u202e') {
				t.Fatalf("unsafe diagnostic text: got %q want %q", got, tc.want)
			}
		})
	}
}

func TestDoctorTerminalEscapesUntrustedWorkspacePaths(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Windows disallows control characters in path names")
	}
	root := filepath.Join(t.TempDir(), "workspace\x1b[2J\n\u202e")
	if err := os.Mkdir(root, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "test\x1b[2J\n.csproj"), []byte("<Project/>"), 0600); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	exit := run(context.Background(), []string{"doctor", root}, &stdout, &stderr)
	if exit != 0 && exit != 1 {
		t.Fatalf("doctor exit=%d stderr=%q", exit, stderr.String())
	}
	out := stdout.String()
	if strings.ContainsRune(out, '\x1b') || strings.ContainsRune(out, '\u202e') {
		t.Fatalf("terminal control character in output: %q", out)
	}
	for _, want := range []string{quoteTerminalPath(root), `\x1b`, `\n`, `\u202e`} {
		if !strings.Contains(out, want) {
			t.Fatalf("missing safely escaped value %q in %q", want, out)
		}
	}
	stdout.Reset()
	stderr.Reset()
	if code := run(context.Background(), []string{"doctor", "--json", root}, &stdout, &stderr); code != exit {
		t.Fatalf("JSON exit=%d text exit=%d stderr=%q", code, exit, stderr.String())
	}
	var report struct{ Path string `json:"path"` }
	if err := json.Unmarshal(stdout.Bytes(), &report); err != nil {
		t.Fatal(err)
	}
	if report.Path != root {
		t.Fatalf("JSON path must remain unmodified: got %q want %q", report.Path, root)
	}
}

func TestDoctorErrorEscapesPath(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Windows disallows control characters in path names")
	}
	path := filepath.Join(t.TempDir(), "missing\x1b[2J\n")
	for _, args := range [][]string{{"doctor", path}, {"test", "--dry-run", path}} {
		var stdout, stderr bytes.Buffer
		if code := run(context.Background(), args, &stdout, &stderr); code != 2 {
			t.Fatalf("args=%q exit=%d", args, code)
		}
		if strings.ContainsRune(stderr.String(), '\x1b') || !strings.Contains(stderr.String(), `\x1b`) || !strings.Contains(stderr.String(), `\n`) {
			t.Fatalf("unescaped error for args=%q: %q", args, stderr.String())
		}
	}
}

func TestUnknownCommandEscapesTerminalControls(t *testing.T) {
	var stdout, stderr bytes.Buffer
	if code := run(context.Background(), []string{"bad\x1b[2J\n"}, &stdout, &stderr); code != 2 {
		t.Fatalf("unexpected exit code %d", code)
	}
	if strings.ContainsRune(stderr.String(), '\x1b') || !strings.Contains(stderr.String(), `\x1b`) || !strings.Contains(stderr.String(), `\n`) {
		t.Fatalf("unknown command leaked terminal controls: %q", stderr.String())
	}
}
