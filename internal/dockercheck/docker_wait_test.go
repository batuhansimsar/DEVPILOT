package dockercheck

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

// A Docker CLI can exit while an unrelated descendant retains inherited pipe
// descriptors. The probe must not spend its entire five-second timeout waiting
// for EOF in that case.
func TestSystemCLIBoundsInheritedPipeWait(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("test uses a POSIX shell fixture")
	}
	dir := t.TempDir()
	docker := filepath.Join(dir, "docker")
	script := "#!/bin/sh\nsleep 3 &\nprintf '27.0.0\\n'\n"
	if err := os.WriteFile(docker, []byte(script), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))
	started := time.Now()
	_, err := SystemCLI(context.Background(), "info")
	elapsed := time.Since(started)
	if err == nil || !strings.Contains(err.Error(), "output pipe stayed open") {
		t.Fatalf("expected inherited pipe error, got %v", err)
	}
	if elapsed >= 2*time.Second {
		t.Fatalf("wait for inherited pipe took %s; expected bounded wait", elapsed)
	}
}
