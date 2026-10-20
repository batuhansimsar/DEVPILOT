package dockercheck

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestSystemCLIRedactsFailedCommandOutput(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("uses a POSIX shell fixture")
	}
	const secret = "token=do-not-leak.private.local"
	dir := t.TempDir()
	binary := filepath.Join(dir, "docker")
	script := "#!/bin/sh\nprintf '" + secret + "\\n' >&2\nprintf '" + secret + "\\n'\nexit 23\n"
	if err := os.WriteFile(binary, []byte(script), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))

	out, err := SystemCLI(context.Background(), "info")
	if err == nil || len(out) != 0 {
		t.Fatalf("expected a failed Docker invocation, got out=%q err=%v", out, err)
	}
	if strings.Contains(err.Error(), secret) || !strings.Contains(err.Error(), "exit code 23") {
		t.Fatalf("Docker diagnostics must redact command output but preserve exit code: %q", err)
	}
	for _, detail := range []string{
		Inspect(context.Background(), SystemCLI).Detail,
		List(context.Background(), SystemCLI).Detail,
	} {
		if strings.Contains(detail, secret) || !strings.Contains(detail, "exit code 23") {
			t.Fatalf("Docker report leaked command output: %q", detail)
		}
	}
}
