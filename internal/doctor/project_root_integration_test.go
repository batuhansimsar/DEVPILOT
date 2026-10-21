package doctor

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestInspectRejectsSymlinkedProjectRoot(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink creation may require elevated privileges")
	}
	project := t.TempDir()
	if err := os.WriteFile(filepath.Join(project, "go.mod"), []byte("module example.com/app\n\ngo 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(t.TempDir(), "external-project")
	if err := os.Symlink(project, link); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	if _, err := Inspect(link); err == nil {
		t.Fatal("doctor unexpectedly followed a project-root symlink")
	}
}
