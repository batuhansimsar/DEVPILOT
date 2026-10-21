package doctor

import (
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestValidateProjectRootDoesNotExposeRejectedPath(t *testing.T) {
	secret := "internal-client-credential-directory"
	root := t.TempDir()
	filename := secret + "-config.txt"
	if runtime.GOOS != "windows" {
		filename = "\x1b[31m" + filename + "\n"
	}
	regularFile := filepath.Join(root, filename)
	if err := os.WriteFile(regularFile, []byte("private"), 0600); err != nil {
		t.Fatal(err)
	}

	for _, tc := range []struct {
		name, path string
		wantErr    error
	}{
		{"not a directory", regularFile, nil},
		{"missing directory", filepath.Join(root, secret+"-missing"), os.ErrNotExist},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := validateProjectRoot(tc.path)
			if err == nil || got != "" {
				t.Fatalf("expected an error and empty result; got %q, %v", got, err)
			}
			if strings.Contains(err.Error(), secret) || strings.Contains(err.Error(), root) || strings.ContainsAny(err.Error(), "\x1b\n\r") {
				t.Fatalf("untrusted path exposed in diagnostic: %q", err.Error())
			}
			if tc.wantErr != nil && !errors.Is(err, tc.wantErr) {
				t.Fatalf("lost underlying error category: %v", err)
			}
		})
	}
}
