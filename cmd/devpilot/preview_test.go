package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestPreviewShowsArgumentsSeparately(t *testing.T) {
	var out bytes.Buffer
	printTestPreview(&out, "/path with spaces", "dotnet", []string{"test", "./-odd name.csproj"})
	text := out.String()
	for _, expected := range []string{
		"Dry run: no command executed.",
		`Working directory: "/path with spaces"`,
		`Executable: "dotnet"`,
		`  "test"`,
		`  "./-odd name.csproj"`,
	} {
		if !strings.Contains(text, expected) {
			t.Fatalf("missing %q from output %q", expected, text)
		}
	}
}

func TestPreviewEscapesTerminalControlCharacters(t *testing.T) {
	var out bytes.Buffer
	printTestPreview(&out, "/work\nmalicious", "go", []string{"test", "\x1b[31m./..."})
	text := out.String()
	if strings.Contains(text, "\x1b") || strings.Contains(text, "/work\nmalicious") {
		t.Fatalf("unescaped control characters in output: %q", text)
	}
	if !strings.Contains(text, `"/work\nmalicious"`) || !strings.Contains(text, `"\x1b[31m./..."`) {
		t.Fatalf("escaped strings missing: %q", text)
	}
}
