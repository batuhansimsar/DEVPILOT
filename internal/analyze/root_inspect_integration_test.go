package analyze

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

// A user-selected symlink must not be traversed even when its target is a
// perfectly valid project directory.
func TestInspectRejectsSymlinkedRoot(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink creation may require elevated privileges")
	}
	actual := t.TempDir()
	if err := os.WriteFile(filepath.Join(actual, "secret.go"), []byte("package secret"), 0600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(t.TempDir(), "linked-project")
	if err := os.Symlink(actual, link); err != nil {
		t.Fatal(err)
	}
	if report, err := Inspect(link); err == nil {
		t.Fatalf("symlink root unexpectedly inspected: %+v", report)
	}
}
