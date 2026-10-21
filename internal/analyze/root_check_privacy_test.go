package analyze

import (
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestProjectRootRedactsMissingAndNonDirectoryPaths(t *testing.T) {
	dir := t.TempDir()
	private := filepath.Join(dir, "private-token-workspace")
	if err := os.WriteFile(private, []byte("content"), 0600); err != nil {
		t.Fatal(err)
	}
	tests := []struct {
		name string
		path string
		want error
	}{
		{name: "missing", path: filepath.Join(dir, "hidden-project"), want: os.ErrNotExist},
		{name: "regular file", path: private},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			_, err := projectRoot(tc.path)
			if err == nil {
				t.Fatal("expected invalid directory to be rejected")
			}
			if tc.want != nil && !errors.Is(err, tc.want) {
				t.Fatalf("expected error class %v, got %v", tc.want, err)
			}
			if strings.Contains(err.Error(), dir) || strings.Contains(err.Error(), filepath.Base(tc.path)) {
				t.Fatalf("filesystem path leaked in diagnostic: %q", err)
			}
		})
	}
}

func TestProjectRootRedactsControlCharactersInMissingPath(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Windows does not permit escape sequences in file names")
	}
	path := filepath.Join(t.TempDir(), "sensitive\x1b[2J\nproject")
	_, err := projectRoot(path)
	if err == nil || !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("expected missing-directory error, got %v", err)
	}
	for _, untrusted := range []string{"sensitive", "\\x1b", "\x1b", "\\n", "\n"} {
		if strings.Contains(err.Error(), untrusted) {
			t.Fatalf("untrusted path bytes leaked: %q", err)
		}
	}
}
